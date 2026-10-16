"""E1 Planner: yêu cầu NL + danh mục nguồn thật → PipelineSpec (LLM rút thông tin, code quyết định mode)."""

import json
import logging
import re

from pydantic import ValidationError

from src.agents.nodes.common import memory_notes, usage_of
from src.agents.state import PipelineState
from src.agents.tools.source_stats import column_values, source_stats
from src.config import get_settings
from src.models.schemas import RunStatus
from src.models.sources import DataSource
from src.models.spec import GlossaryUse, ModeSignals, PipelineSpec, decide_mode, decide_options, signals_from_sources
from src.services import secrets, source_registry
from src.services.connectors import ConnectorError, get_connector
from src.services.llm import LLMOutputError, call_llm, parse_json_output, to_json
from src.services.llm_context import LLMContext, context_for_state

logger = logging.getLogger(__name__)


def _key(text: str) -> str:
    return re.sub(r"[\W_]+", " ", str(text)).strip().lower()


def drop_answered(data: dict, answered: list[dict]) -> dict:
    """Bỏ câu hỏi/điểm chưa rõ TRÙNG NGUYÊN VĂN câu người dùng đã trả lời; ghi câu trả lời vào giả định.

    LLM thật đôi khi hỏi lại y hệt câu đã trả lời; con người đã quyết định nên code không hỏi lại lần nữa.
    """
    done = {_key(item["question"]): f"{item['question']} → {item['answer']}" for item in answered}
    if not done:
        return data
    questions = [q for q in data.get("questions") or [] if _key(q.get("question", "")) not in done]
    unknowns = [u for u in data.get("unknowns") or [] if _key(u) not in done]
    assumptions = list(dict.fromkeys([*(data.get("assumptions") or []), *done.values()]))
    return {**data, "questions": questions, "unknowns": unknowns, "assumptions": assumptions}


def fill_sources(data: dict, catalog: list[dict]) -> dict:
    """Planner chỉ trả TÊN nguồn; `kind`/`path` lấy từ danh mục thật (tên lạ để kind rỗng → V0 chặn)."""
    known = {item["name"]: item for item in catalog}
    sources = []
    for item in data.get("sources") or []:
        name = str(item if isinstance(item, str) else item.get("name", ""))
        info = known.get(name, {})
        sources.append({"name": name, "kind": info.get("kind", ""), "path": info.get("path", "")})
    return {**data, "sources": sources}


def build_spec(data: dict, request_text: str, answers: dict[str, str]) -> PipelineSpec:
    """Dựng spec từ JSON của LLM; tín hiệu loại nguồn và `mode` do code tính lại."""
    spec = PipelineSpec.model_validate({**data, "request_text": request_text, "decisions": answers})
    signals = signals_from_sources(spec.sources, ModeSignals.model_validate(data.get("signals") or {}))
    mode, reason = decide_mode(signals)
    return spec.model_copy(update={"signals": signals, "mode": mode, "mode_reason": reason})


def _row_counts(items: list[dict]) -> dict[str, int | None]:
    """Số dòng từng nguồn được chọn, do CODE đo qua bộ nạp (không gửi LLM); không đo được thì None."""
    sources: dict[int, DataSource] = {}
    counts: dict[str, int | None] = {}
    for item in items:
        counts[item["name"]] = None
        try:
            if item.get("source_id") is None:
                counts[item["name"]] = source_stats(item).get("rows")
                continue
            if not sources:
                sources.update({s.id: s for s in source_registry.list_sources()})
            if source := sources.get(item["source_id"]):
                counts[item["name"]] = get_connector(source).row_count(item["name"])
        except (ConnectorError, secrets.SecretError, OSError) as exc:  # nguồn tạm lỗi: nạp toàn bộ cho chắc
            logger.warning("row count unavailable", extra={"table": item["name"], "reason": str(exc)[:150]})
    return counts


def with_pipeline_options(spec: PipelineSpec, catalog: list[dict], overrides: dict[str, str]) -> PipelineSpec:
    """Điền `options` (nạp toàn bộ/phần mới, lịch chạy, kết nối) bằng luật cố định; lựa chọn DE đã đặt ở J1b được giữ lại."""
    chosen = [i for i in catalog if i["name"] in {s.name for s in spec.sources}]
    options = decide_options(spec.request_text, chosen, _row_counts(chosen), overrides)
    return spec.model_copy(update={"options": options})


def with_value_options(spec: PipelineSpec, catalog: list[dict]) -> PipelineSpec:
    """Câu hỏi về giá trị một cột: code thay lựa chọn của LLM bằng giá trị thật để người tick (LLM không thấy).

    Không tìm thấy cột, hoặc cột có quá nhiều/quá ít giá trị: giữ lựa chọn của LLM như câu hỏi thường.
    """
    questions = []
    for question in spec.questions:
        values, normalized = column_values(catalog, question.column) if question.column else ([], False)
        update = {"options": values, "multiple": True, "normalized": normalized} if values else {"column": ""}
        questions.append(question.model_copy(update=update))
    return spec.model_copy(update={"questions": questions})


def planner_variables(state: PipelineState, context: LLMContext, last_round: bool) -> dict[str, str]:
    """Biến điền vào prompt planner."""
    answers = state.get("answers", {})
    glossary = context.glossary_for(state["request_text"])  # cửa duy nhất; tối đa N thuật ngữ khớp yêu cầu
    return {
        "request_text": state["request_text"],
        "source_catalog": to_json(context.planner_catalog()),  # cửa duy nhất: mức truy cập theo từng nguồn
        "glossary": to_json(glossary) if glossary else "(không có)",
        "answers": to_json(answers) if answers else "(chưa có)",  # không có trong prompt; LLM mock đọc
        "answered_questions": to_json(state.get("answered", [])) if state.get("answered") else "(chưa có)",
        "spec_errors": to_json(state.get("spec_errors", [])),
        "plan_feedback": to_json(state.get("plan_feedback", [])) if state.get("plan_feedback") else "(chưa có)",
        "memory_notes": to_json(memory_notes(state)),
        "round_note": "ĐÂY LÀ LƯỢT CUỐI: không được hỏi thêm." if last_round else "(chưa phải lượt cuối)",
    }


def used_terms(variables: dict[str, str]) -> list[GlossaryUse]:
    """Thuật ngữ đã đưa vào prompt (code ghi lại, không nhờ LLM kể) để hiện ở màn Duyệt kế hoạch."""
    raw = variables.get("glossary", "")
    if not raw.startswith("["):
        return []
    return [GlossaryUse(term=item["term"], definition=item.get("definition", "")) for item in json.loads(raw)]


def planner_node(state: PipelineState) -> dict:
    """Gọi LLM lập đặc tả; lỗi định dạng được trả về `spec_errors` để V0 cho làm lại."""
    context = context_for_state(
        state, audit=not state.get("source_catalog"), glossary=True
    )  # lần đầu: ghi AuditLog nguồn nào, mức nào
    catalog = context.catalog
    rounds = state.get("plan_rounds", 0) + 1
    if not catalog:
        return {
            "status": RunStatus.FAILED.value,
            "error": "Bạn chưa được cấp quyền xem nguồn dữ liệu nào hoặc chưa có dữ liệu (quản trị viên đăng ký nguồn; demo: python -m src.cli seed).",
        }
    answers = state.get("answers", {})
    last_round = rounds >= get_settings().max_plan_rounds
    variables = planner_variables(state, context, last_round)
    response = call_llm("planner", variables)
    base = {"source_catalog": catalog, "plan_rounds": rounds, "llm_usage": usage_of(response)}
    try:
        data = fill_sources(drop_answered(parse_json_output(response.text), state.get("answered", [])), catalog)
        spec = with_value_options(build_spec(data, state["request_text"], answers), catalog)
        spec = with_pipeline_options(spec, catalog, state.get("plan_options", {}))
        spec = spec.model_copy(update={"glossary_used": used_terms(variables)})
    except (LLMOutputError, ValidationError) as exc:
        logger.warning("planner output invalid", extra={"error": str(exc)[:300]})
        return {**base, "spec": {}, "spec_errors": [f"Planner trả về đặc tả sai định dạng: {str(exc)[:200]}"]}
    return {**base, "spec": spec.model_dump(mode="json")}
