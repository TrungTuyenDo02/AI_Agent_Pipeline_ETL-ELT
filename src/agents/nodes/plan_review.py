"""J1b Duyệt kế hoạch: graph tạm dừng, DE đọc kế hoạch có giải thích rồi đồng ý (sinh code) hoặc ghi chú để sửa.

Kế hoạch do Planner viết (lời LLM, chưa kiểm chứng); nếu Planner bỏ trống thì code dựng kế hoạch tối thiểu từ đặc tả
để DE luôn có thứ để duyệt. Đặt bước này trước khi sinh code để không tốn token cho kế hoạch sai.
"""

from langgraph.types import interrupt

from src.agents.state import PipelineState
from src.models.contracts import PlanDecision, hand_off
from src.models.spec import LOAD_LABELS, SCHEDULE_LABELS, PipelineOptions, apply_overrides

PLAN_SPEC_FIELDS = (
    "target", "mode", "mode_reason", "grain", "output_columns", "metrics", "filters", "assumptions", "options",
    "glossary_used",
)  # fmt: skip
OPTION_KEYS = ("load_mode", "schedule", "incremental_column")
NEXT_STEPS = (
    "Sau khi bạn đồng ý: nạp nguồn vào sandbox → soi dữ liệu → sinh model dbt + DAG → Tester độc lập viết test "
    "(không xem code) → chạy thử trong sandbox → tối ưu nếu đáng → bạn duyệt code (J2)."
)


def _names(items: list[dict], key: str = "name") -> str:
    return ", ".join(str(item.get(key, "")) for item in items) or "—"


def default_plan(spec: dict) -> list[dict]:
    """Kế hoạch tối thiểu dựng bằng code từ đặc tả (khi Planner không viết phần giải thích)."""
    metrics = "; ".join(f"{m.get('name')}: {m.get('description')}" for m in spec.get("metrics", [])) or "—"
    return [
        {
            "title": "Nạp nguồn",
            "detail": f"Đọc các bảng: {_names(spec.get('sources', []))}.",
            "reason": "Đây là các nguồn chứa dữ liệu yêu cầu cần.",
        },
        {
            "title": "Làm sạch (staging)",
            "detail": "Chuẩn hóa ngày, tiền, mã và trạng thái của từng nguồn về cùng một dạng.",
            "reason": "Dữ liệu thô mỗi nguồn ghi một kiểu; phải thống nhất trước khi gộp.",
        },
        {
            "title": f"Tính bảng đích {spec.get('target', '')}",
            "detail": f"Mỗi dòng là một {', '.join(spec.get('grain', [])) or '—'}; chỉ số: {metrics}.",
            "reason": "Đúng mức gộp và chỉ số yêu cầu nêu.",
        },
        {
            "title": "Áp dụng điều kiện lọc",
            "detail": "; ".join(spec.get("filters", [])) or "Không có điều kiện lọc riêng.",
            "reason": "Theo yêu cầu và câu trả lời làm rõ.",
        },
    ]


def _chosen_columns(spec: dict, catalog: list[dict]) -> list[str]:
    """Cột của các nguồn được chọn (để DE chọn cột thời gian khi nạp phần mới)."""
    names = {s.get("name") for s in spec.get("sources", [])}
    return sorted({c for item in catalog if item.get("name") in names for c in item.get("columns", {})})


def plan_payload(spec: dict, catalog: list[dict] | None = None, drift_warnings: list[dict] | None = None) -> dict:
    """Nội dung hiển thị cho DE ở J1b."""
    steps = spec.get("plan") or default_plan(spec)
    return {
        "kind": "plan",
        "summary": spec.get("plan_summary")
        or f"Tạo bảng {spec.get('target', '')} từ {_names(spec.get('sources', []))}.",
        "steps": steps,
        "spec": {key: spec.get(key) for key in PLAN_SPEC_FIELDS},
        "sources": [s.get("name") for s in spec.get("sources", [])],
        "next_steps": NEXT_STEPS,
        "time_columns": _chosen_columns(spec, catalog or []),
        "drift_warnings": drift_warnings or [],  # thay đổi cấu trúc nguồn mức info/warning (không chặn)
        "option_choices": {  # giá trị DE được chọn ở J1b (mặc định là lựa chọn code đề xuất trong spec.options)
            "load_mode": [{"value": k, "label": v} for k, v in LOAD_LABELS.items()],
            "schedule": [{"value": k, "label": v} for k, v in SCHEDULE_LABELS.items()],
        },
    }


def _clean_options(reply: dict) -> dict[str, str]:
    """Chỉ giữ khóa và giá trị hợp lệ của lựa chọn pipeline (chuỗi ngắn, đúng danh sách); còn lại bỏ."""
    options = reply.get("options")
    if not isinstance(options, dict):
        return {}
    allowed = {"load_mode": set(LOAD_LABELS), "schedule": set(SCHEDULE_LABELS)}
    clean = {k: str(v) for k, v in options.items() if k in allowed and str(v) in allowed[k]}
    column = str(options.get("incremental_column") or "").strip()
    if column and len(column) <= 128:
        clean["incremental_column"] = column
    return clean


def parse_plan_reply(reply: object) -> dict | None:
    """Quyết định hợp lệ: đồng ý (kèm lựa chọn pipeline nếu có), hoặc yêu cầu sửa kèm ghi chú; còn lại trả về None."""
    if not isinstance(reply, dict):
        return None
    decision, note = reply.get("decision"), str(reply.get("note") or "").strip()
    options = _clean_options(reply)
    extra = {"options": options} if options else {}
    if decision == "approve":
        return hand_off(PlanDecision, {"decision": "approve", "note": note, **extra})
    if decision == "revise" and note:
        return hand_off(PlanDecision, {"decision": "revise", "note": note, **extra})
    return None


def _spec_with_choice(spec: dict, choice: dict[str, str], catalog: list[dict]) -> dict:
    """Spec với lựa chọn pipeline của DE đã áp vào `options`: giá trị phải hợp lệ, cột thời gian phải có thật ở nguồn được chọn."""
    if not choice or not spec:
        return spec
    names = {s.get("name") for s in spec.get("sources", [])}
    columns = [list(item.get("columns", {})) for item in catalog if item.get("name") in names]
    options = apply_overrides(PipelineOptions.model_validate(spec.get("options") or {}), choice, columns)
    return {**spec, "options": options.model_dump(mode="json")}


def plan_review_node(state: PipelineState) -> dict:
    """Tạm dừng chờ DE; sửa → ghi chú chuyển cho Planner lập lại kế hoạch; đồng ý → lựa chọn pipeline của DE vào spec."""
    catalog = state.get("source_catalog", [])
    warnings = (state.get("drift") or {}).get("warnings", [])
    reply = parse_plan_reply(interrupt(plan_payload(state.get("spec", {}), catalog, warnings)))
    if reply is None:
        return {"plan_review": {"invalid": True}}
    choice = reply.get("options", {})
    merged = {**state.get("plan_options", {}), **choice}
    if reply["decision"] == "approve":
        return {
            "plan_review": reply,
            "spec": _spec_with_choice(state.get("spec", {}), choice, catalog),
            "plan_options": merged,
        }
    return {
        "plan_review": reply,
        "plan_feedback": [*state.get("plan_feedback", []), reply["note"]],
        "plan_reviews": state.get("plan_reviews", 0) + 1,
        "plan_options": merged,
    }
