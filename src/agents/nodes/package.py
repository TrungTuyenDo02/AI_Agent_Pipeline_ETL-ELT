"""Gói "Pull Request" để duyệt: bằng chứng tách `measured` (code đo) và `claimed` (LLM nói)."""

import json
import logging
from pathlib import Path

from src.agents.nodes.common import sandbox_db
from src.agents.review_gate import review_gate
from src.agents.state import PipelineState
from src.agents.tools.bottleneck import analyze_bottlenecks
from src.agents.tools.sql_tools import value_filters
from src.config import get_settings
from src.models.evidence import Evidence, MeasuredItem
from src.models.schemas import RunStatus
from src.services.schema_watch import SchemaReport

logger = logging.getLogger(__name__)


def _spec_items(state: PipelineState) -> list[MeasuredItem]:
    spec = state.get("spec", {})
    rows = ", ".join(f"{k}: {v}" for k, v in state.get("row_counts", {}).items())
    return [
        MeasuredItem(node="V0 Soát spec", check="Đặc tả đủ trường, không còn điểm chưa rõ", result="Đạt", passed=True),
        MeasuredItem(
            node="V0 Soát spec", check="Chế độ pipeline", result=f"{spec.get('mode')} — {spec.get('mode_reason')}"
        ),
        MeasuredItem(node="E0 Nhận nguồn", check="Số dòng nạp vào sandbox", result=rows or "—"),
    ]


def _run_items(state: PipelineState) -> list[MeasuredItem]:
    sandbox, safety = state.get("sandbox", {}), state.get("safety", {})
    return [
        MeasuredItem(
            node="V1 An toàn",
            check="Lệnh nguy hiểm, tên bảng/cột bịa",
            result="Không phát hiện",
            passed=safety.get("passed"),
        ),
        MeasuredItem(
            node="V2 Sandbox",
            check="dbt build (model)",
            passed=sandbox.get("passed"),
            result=f"{sandbox.get('models_ok', 0)}/{sandbox.get('models_total', 0)} model chạy được",
        ),
        MeasuredItem(
            node="V2 Sandbox",
            check="dbt test (đối soát, grain, not_null)",
            passed=sandbox.get("passed"),
            result=f"{sandbox.get('tests_ok', 0)}/{sandbox.get('tests_total', 0)} test đạt",
        ),
        MeasuredItem(node="V2 Sandbox", check="Số dòng bảng đích", result=str(sandbox.get("target_rows", "—"))),
        MeasuredItem(
            node="Vòng sửa",
            check="Số lần sửa / cứu hộ",
            result=f"{state.get('fix_attempts', 0)} lần sửa, {state.get('rescue_count', 0)} lần cứu hộ",
        ),
    ]


def _required_items(state: PipelineState) -> list[MeasuredItem]:
    """Cổng duyệt vào bằng chứng: chưa kiểm chứng → passed=None (không tính là đạt)."""
    gate = review_gate(state)
    label = {"passed": "Đạt", "failed": "Không đạt", "unverified": "Chưa kiểm chứng"}
    return [
        MeasuredItem(
            node=node,
            check=c.name,
            result=f"{label[c.status]}: {c.reason}",
            passed={"passed": True, "failed": False}.get(c.status),
        )
        for node, items in (("Kiểm tra bắt buộc", gate.checks), ("Bổ sung", gate.extra))
        for c in items
    ]


def spec_text(state: PipelineState) -> str:
    """Mọi chữ người dùng/đặc tả đã nêu: giá trị lọc hợp lệ chỉ được lấy từ đây (mục 9)."""
    answered = " ".join(f"{a.get('question', '')} {a.get('answer', '')}" for a in state.get("answered", []))
    spec = json.dumps(state.get("spec", {}), ensure_ascii=False)
    return " ".join([state.get("request_text", ""), answered, spec, *state.get("plan_feedback", [])])


def find_value_filters(state: PipelineState) -> list[dict]:
    """Điều kiện cứng theo giá trị trong các model (sắp theo file, dòng)."""
    text = spec_text(state)
    found = [
        item
        for path, sql in state.get("code_files", {}).items()
        if path.startswith("models/") and path.endswith(".sql")
        for item in value_filters(path, sql, text)
    ]
    return sorted(found, key=lambda f: (f["file"], f["line"]))


def _data_rule_items(state: PipelineState, filters: list[dict]) -> list[MeasuredItem]:
    """Mục 8–9: cấu trúc nguồn so với bản đã duyệt, số dòng vào/ra, điều kiện cứng theo giá trị."""
    report = SchemaReport.model_validate(state.get("schema_report") or {"checked": False, "note": "Chưa soát."})
    changed = any(c.added or c.removed or c.type_changed or c.new_values for c in report.changes)
    items = [
        MeasuredItem(
            node="Vs Cấu trúc nguồn",
            check="So với bản Reviewer đã duyệt",
            result=report.summary(),
            passed=(not changed) if report.checked else None,
        )
    ]
    for rec in state.get("reconciliation", []):
        dropped = rec["rows_in"] - rec["rows_out"]
        note = "khớp" if dropped == 0 else (f"loại {dropped} dòng" if dropped > 0 else f"nhân thêm {-dropped} dòng")
        items.append(
            MeasuredItem(
                node="V2 Đối chiếu số dòng",
                check=f"{rec['source']} → {rec['model']}",
                result=f"{rec['rows_in']} vào → {rec['rows_out']} ra ({note}; cần lý do ghi rõ nếu khác)",
                passed=True if dropped == 0 else None,
            )
        )
    for table, info in state.get("profile", {}).items():
        for column, col in info.get("columns", {}).items():
            for note in col.get("uncertain", []):
                items.append(
                    MeasuredItem(node="P Soi dữ liệu", check=f"Định dạng chưa chắc: {table}.{column}", result=note)
                )
    outside = [f for f in filters if not f["in_spec"]]
    items.append(
        MeasuredItem(
            node="Điều kiện theo giá trị",
            check="So sánh cột với giá trị cụ thể (tô sáng ở màn duyệt)",
            result=f"{len(filters)} điều kiện, {len(outside)} giá trị không có trong đặc tả/câu trả lời",
            passed=True if not outside else None,
        )
    )
    return items


def _patch_items(state: PipelineState) -> list[MeasuredItem]:
    """Bản vá nhanh: bao nhiêu thay đổi, sửa bằng code hay AI, và bảng đích có giống lần chạy gốc không (đo bằng code)."""
    patch = state.get("patch") or {}
    if not patch:
        return []
    plan = patch.get("plan") or {}
    tokens = sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in state.get("llm_usage", []))
    items = [
        MeasuredItem(
            node="P Bản vá",
            check="Thay đổi nguồn đã xử lý",
            result=(
                f"{len(plan.get('items', []))} thay đổi: {len(patch.get('applied', []))} file sửa bằng code, "
                f"{len(patch.get('llm_files', []))} file cần AI; {tokens} token"
            ),
            passed=True,
        )
    ]
    regression = patch.get("regression") or {}
    if regression.get("compared"):
        same = regression["same"]
        result = (
            f"Bảng đích giống hệt lần chạy gốc ({regression['rows_after']} dòng)"
            if same
            else f"Bảng đích khác lần chạy gốc: {regression['rows_before']} → {regression['rows_after']} dòng, {regression['differing_rows']} dòng khác"
        )
        if regression.get("schema_same") is False:
            result += "; " + regression["note"]
        items.append(
            MeasuredItem(node="P Bản vá", check="So với lần chạy gốc", result=result, passed=True if same else None)
        )
    elif regression:
        items.append(
            MeasuredItem(node="P Bản vá", check="So với lần chạy gốc", result=str(regression.get("note", "—")))
        )
    return items


def _optimization_items(state: PipelineState) -> list[MeasuredItem]:
    report = state.get("optimization", {})
    if not report:
        return []
    items = [
        MeasuredItem(node="V3 Đối chiếu", check=f"Kết quả bộ '{c['dataset']}'", result=c["detail"], passed=c["equal"])
        for c in report.get("equivalence", [])
    ]
    before, after = report.get("before") or {}, report.get("after") or {}
    timing = f"{before.get('median_ms', '—')} ms → {after.get('median_ms', '—')} ms" if before else "—"
    items.append(MeasuredItem(node="E4/V3 Tối ưu", check="Thời gian trung vị trên bộ large", result=timing))
    items.append(
        MeasuredItem(node="E4/V3 Tối ưu", check="Quyết định", result=f"{report['decision']}: {report['reason']}")
    )
    return items + _perf_items(report.get("bottlenecks"))


def _ms(value: float | None) -> str:
    return "chưa đo" if value is None else f"{value:.1f} ms"


def _perf_items(perf: dict | None) -> list[MeasuredItem]:
    """Hai con số tách biệt (tổng các model ≠ thời gian thực) + model chậm nhất. Giả thuyết không vào `measured`."""
    if not perf or not perf.get("measured"):
        return [MeasuredItem(node="Đo hiệu năng", check="Thời gian từng model", result="chưa đo")] if perf else []
    items = [
        MeasuredItem(node="Đo hiệu năng", check="Tổng thời gian các model", result=_ms(perf.get("model_total_ms"))),
        MeasuredItem(node="Đo hiệu năng", check="Thời gian lệnh dbt build", result=_ms(perf.get("dbt_wall_ms"))),
        MeasuredItem(node="Đo hiệu năng", check="Thời gian toàn DAG (Airflow)", result=_ms(perf.get("dag_wall_ms"))),
    ]
    for f in perf.get("findings", []):
        result = (
            f["phenomenon"] + (" " + "; ".join(f["evidence"]) if f["evidence"] else "")
            if f["analyzed"]
            else f["unknown"]
        )
        items.append(MeasuredItem(node="Điểm nghẽn", check=f"#{f['rank']} {f['model']}", result=result))
    return items


def with_bottlenecks(state: PipelineState) -> dict:
    """Gắn báo cáo điểm nghẽn vào báo cáo tối ưu (tùy chọn). Lỗi → ghi "chưa phân tích được", không làm hỏng pipeline."""
    report = state.get("optimization") or {}
    if not report or not state.get("workspace"):
        return report
    settings = get_settings()
    try:
        perf = analyze_bottlenecks(
            Path(state["workspace"]),
            sandbox_db(state),
            state.get("sandbox") or {},
            settings.perf_top_n,
            settings.perf_analyze_sec,
        ).model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001 — bước phân tích là phụ
        logger.warning("bottleneck analysis failed", extra={"error": type(exc).__name__})
        perf = {"measured": False, "note": f"Chưa phân tích được: {type(exc).__name__}."}
    return {**report, "bottlenecks": perf}


def build_evidence(state: PipelineState, filters: list[dict] | None = None) -> Evidence:
    """Bằng chứng đầy đủ cho Reviewer."""
    claimed = [*state.get("code_notes", []), *state.get("test_notes", [])]
    explanation = state.get("optimization", {}).get("explanation")
    if explanation:
        claimed.append(f"Optimizer: {explanation}")
    filters = find_value_filters(state) if filters is None else filters
    measured = (
        _required_items(state)
        + _spec_items(state)
        + _run_items(state)
        + _patch_items(state)
        + _data_rule_items(state, filters)
        + _optimization_items(state)
    )
    return Evidence(measured=measured, claimed=claimed)


def _plan_lines(spec: dict) -> list[str]:
    """Kế hoạch DE đã duyệt ở J1b (lời LLM) — giúp người xem PR hiểu vì sao code viết như vậy."""
    steps = spec.get("plan") or []
    if not steps:
        return []
    numbered = [
        f"{i}. **{s.get('title')}** — {s.get('detail')} _(Vì sao: {s.get('reason')})_" for i, s in enumerate(steps, 1)
    ]
    return ["## Kế hoạch đã duyệt (J1b)", "", spec.get("plan_summary", ""), "", *numbered, ""]


def write_pr_description(state: PipelineState, evidence: Evidence) -> None:
    """Ghi PULL_REQUEST.md vào workspace (mô tả để Engineer mở PR thật sau khi được duyệt)."""
    lines = [
        f"# Pipeline: {state.get('spec', {}).get('target')}",
        "",
        f"Yêu cầu: {state.get('request_text')}",
        "",
        *_plan_lines(state.get("spec", {})),
        "## Code đo (measured)",
        *[f"- [{m.node}] {m.check}: {m.result}" for m in evidence.measured],
        "",
        "## LLM nói (claimed, chưa kiểm chứng)",
        *[f"- {c}" for c in evidence.claimed],
        "",
    ]
    (Path(state["workspace"]) / "PULL_REQUEST.md").write_text("\n".join(lines), encoding="utf-8")


def package_node(state: PipelineState) -> dict:
    """Đóng gói bằng chứng (kèm báo cáo điểm nghẽn), chuyển sang chờ duyệt."""
    filters = find_value_filters(state)
    optimization = with_bottlenecks(state)
    evidence = build_evidence({**state, "optimization": optimization}, filters)
    write_pr_description(state, evidence)
    update = {"evidence": evidence.model_dump(), "value_filters": filters, "status": RunStatus.WAITING_REVIEW.value}
    return {**update, "optimization": optimization} if optimization else update
