"""Gói "Pull Request" để duyệt: bằng chứng tách `measured` (code đo) và `claimed` (LLM nói)."""

import json
from pathlib import Path

from src.agents.state import PipelineState
from src.agents.tools.sql_tools import value_filters
from src.models.evidence import Evidence, MeasuredItem
from src.models.schemas import RunStatus
from src.services.schema_watch import SchemaReport


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
    return items


def build_evidence(state: PipelineState, filters: list[dict] | None = None) -> Evidence:
    """Bằng chứng đầy đủ cho Reviewer."""
    claimed = [*state.get("code_notes", []), *state.get("test_notes", [])]
    explanation = state.get("optimization", {}).get("explanation")
    if explanation:
        claimed.append(f"Optimizer: {explanation}")
    filters = find_value_filters(state) if filters is None else filters
    measured = (
        _spec_items(state)
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
    """Đóng gói bằng chứng, chuyển sang chờ duyệt."""
    filters = find_value_filters(state)
    evidence = build_evidence(state, filters)
    write_pr_description(state, evidence)
    return {"evidence": evidence.model_dump(), "value_filters": filters, "status": RunStatus.WAITING_REVIEW.value}
