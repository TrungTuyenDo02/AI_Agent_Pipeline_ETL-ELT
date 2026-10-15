"""Trạng thái từng nút E/V/J của một lần chạy cho "đường ống tiến trình" trên web (U9, mục 7.3-3).

Chỉ suy ra từ dữ liệu thật: nhật ký bước (`events`, chỉ có trong phiên máy chủ đang chạy), node đang chạy (sự kiện
"bắt đầu node" của LangGraph), state đã lưu ở checkpoint, câu hỏi đang chờ người và trạng thái lần chạy.
Không đoán: thiếu dữ liệu thì nút ở trạng thái "chờ".
"""

from pydantic import BaseModel

# (id, mã, tên, loại E/V/J, các node graph thuộc nút này, nút tùy chọn — chỉ hiện khi đã xảy ra)
STAGES: list[tuple[str, str, str, str, tuple[str, ...], bool]] = [
    ("input_gate", "G0", "Kiểm tra đầu vào", "V", ("input_gate", "input_info"), True),
    ("drift_gate", "G1", "Kiểm tra cấu trúc nguồn", "V", ("drift_gate",), True),
    ("patch", "P", "Vá theo thay đổi nguồn", "E", ("patch_start", "patch_apply", "patch_verify"), True),
    ("planner", "E1", "Lập kế hoạch", "E", ("planner",), False),
    ("clarify", "J1", "Hỏi làm rõ", "J", ("clarify",), True),
    ("spec_check", "V0", "Soát đặc tả", "V", ("spec_check",), False),
    ("plan_review", "J1b", "Duyệt kế hoạch", "J", ("plan_review",), False),
    ("prepare", "E0–E2", "Nạp và soi dữ liệu", "E", ("ingest", "profiler", "mock_data"), False),
    ("schema", "Vs", "Soát cấu trúc nguồn", "V", ("schema_guard",), False),
    ("codegen", "E3", "Sinh code", "E", ("codegen",), False),
    ("testgen", "E3b", "Sinh test", "E", ("testgen",), False),
    ("safety", "V1", "Kiểm an toàn", "V", ("safety",), False),
    ("sandbox", "V2", "Chạy thử", "V", ("sandbox_run",), False),
    ("rescue", "J", "Cứu hộ", "J", ("rescue",), True),
    ("optimizer", "E4", "Tối ưu", "E", ("optimizer",), False),
    ("compare", "V3", "Đối chiếu", "V", ("compare",), False),
    ("review", "J2", "Duyệt code", "J", ("review", "package", "finalize"), False),
]
PENDING_STAGE = {
    "drift": "drift_gate",
    "input": "input_gate",
    "clarify": "clarify",
    "plan": "plan_review",
    "schema": "schema",
    "rescue": "rescue",
    "review": "review",
}
REUSED_IN_PATCH = {
    "planner",
    "spec_check",
    "plan_review",
}  # run vá mang sẵn đặc tả đã duyệt: các bước này không chạy lại
FIX_LOOP = {"safety", "sandbox"}  # V1/V2 lỗi → quay về E3 sửa


class Stage(BaseModel):
    """Một nút trên đường ống. `state`: waiting | running | passed | failed | human."""

    id: str
    code: str
    label: str
    kind: str
    state: str
    detail: str = ""


def _from_values(stage_id: str, values: dict, status: str) -> tuple[str, str] | None:
    """Trạng thái suy từ state đã lưu (khi không còn nhật ký bước, ví dụ sau khi khởi động lại máy chủ)."""
    safety, sandbox = values.get("safety") or {}, values.get("sandbox") or {}
    optimization = values.get("optimization") or {}
    checks: dict[str, tuple[str, str] | None] = {
        "input_gate": ("passed", "") if (values.get("input_gate") or {}).get("status") == "ok" else None,
        "drift_gate": ("passed", "") if (values.get("drift") or {}).get("checked") else None,
        "patch": ("passed", "") if (values.get("patch") or {}).get("applied") is not None else None,
        "planner": ("passed", "") if values.get("spec") else None,
        "clarify": ("passed", f"{len(values['answered'])} câu đã trả lời") if values.get("answered") else None,
        "spec_check": ("passed", "") if values.get("plan_review") or values.get("workspace") else None,
        "plan_review": ("passed", "đã đồng ý")
        if (values.get("plan_review") or {}).get("decision") == "approve"
        else None,
        "prepare": ("passed", f"{len(values['profile'])} bảng") if values.get("profile") else None,
        "schema": ("passed", "") if values.get("schema_report") and values.get("code_files") else None,
        "codegen": ("passed", f"{len(values['code_files'])} file") if values.get("code_files") else None,
        "testgen": ("passed", f"{len(values['test_files'])} file test") if values.get("test_files") else None,
        "safety": (("passed" if safety["passed"] else "failed"), "") if "passed" in safety else None,
        "sandbox": (("passed" if sandbox["passed"] else "failed"), "") if "passed" in sandbox else None,
        "rescue": ("passed", f"{values['rescue_count']} lần") if values.get("rescue_count") else None,
        "optimizer": ("passed", "") if optimization or values.get("opt_candidate") else None,
        "compare": ("passed", str(optimization.get("decision", ""))) if optimization.get("decision") else None,
        "review": ("passed", "đã duyệt") if status == "approved" else None,
    }
    return checks.get(stage_id)


def _from_events(nodes: tuple[str, ...], events: list[dict]) -> tuple[str, str] | None:
    """Lần chạy gần nhất của các node thuộc nút (vòng sửa có thể chạy một nút nhiều lần)."""
    last = next((e for e in reversed(events) if e.get("node") in nodes), None)
    if last is None:
        return None
    return ("passed" if last.get("ok") else "failed"), str(last.get("detail", ""))


def stage_of(node: str) -> str | None:
    """Nút trên đường ống chứa node graph `node`."""
    return next((s[0] for s in STAGES if node in s[4]), None)


def _running_stage(events: list[dict], ids: list[str], current_node: str | None = None) -> str | None:
    """Nút đang chạy: theo node đang chạy thật nếu biết; nếu không, nút kế tiếp sau bước vừa xong (V1/V2 lỗi → E3)."""
    if current_node and (found := stage_of(current_node)):
        return found
    if not events:
        return next(
            s for s in ids if s not in ("input_gate", "drift_gate", "patch")
        )  # hai cửa chỉ hiện khi đã chạy (nút tùy chọn)
    stage = stage_of(str(events[-1].get("node")))
    if stage is None:
        return None
    if stage in FIX_LOOP and not events[-1].get("ok"):
        return "codegen"
    if stage == "planner":
        return "spec_check"
    later = ids[ids.index(stage) + 1 :] if stage in ids else []
    return next((s for s in later if s not in ("clarify", "rescue")), None)


def pipeline_stages(
    values: dict, events: list[dict], pending: dict | None, status: str, busy: bool, current_node: str | None = None
) -> list[Stage]:
    """Danh sách nút theo đúng thứ tự luồng thật, mỗi nút có trạng thái từ dữ liệu thật."""
    human = PENDING_STAGE.get((pending or {}).get("kind", "")) if not busy else None
    ids = [s[0] for s in STAGES]
    running = _running_stage(events, ids, current_node) if busy else None
    stages: list[Stage] = []
    for stage_id, code, label, kind, nodes, optional in STAGES:
        found = _from_events(nodes, events) or _from_values(stage_id, values, status)
        state, detail = found or ("waiting", "")
        if values.get("patch_of") and stage_id in REUSED_IN_PATCH:
            state, detail = "passed", "dùng lại từ lần chạy gốc"
        if stage_id == human:
            state, detail = "human", "chờ bạn"
        elif stage_id == running:
            state, detail = "running", "đang chạy"
        if optional and state == "waiting":
            continue
        stages.append(Stage(id=stage_id, code=code, label=label, kind=kind, state=state, detail=detail[:140]))
    if status == "failed" and not any(s.state == "failed" for s in stages):
        first_open = next((s for s in stages if s.state in ("waiting", "running")), None)
        if first_open:
            first_open.state, first_open.detail = "failed", "dừng tại đây"
    return stages
