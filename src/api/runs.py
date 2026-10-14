"""Lần chạy: tạo (chạy nền), xem tiến trình/chi tiết/file, tải gói code, trả lời J1, duyệt kế hoạch J1b, cứu hộ.

Thao tác làm graph chạy tiếp trả về 202 ngay; web hỏi `GET /runs/{id}` định kỳ để thấy tiến trình.
Xem: mọi người đã đăng nhập. Tạo yêu cầu, trả lời, duyệt kế hoạch, cứu hộ: chỉ Engineer (kiểm ở backend).
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from src.agents import runner
from src.agents.nodes.clarify import valid_answers
from src.agents.runner import ResumeRequest, RunStateError
from src.agents.stages import pipeline_stages, stage_of
from src.api.deps import (
    CurrentUser,
    Engineer,
    LoggedIn,
    client_ip,
    run_for_user,
    run_or_404,
    run_visible_to,
    visible_table_names,
)
from src.api.requests import (
    Accepted,
    AnswerBody,
    CreateRunBody,
    InputBody,
    PlanBody,
    RescueBody,
    RunDetail,
    RunFiles,
    SchemaBody,
)
from src.models.schemas import RunRecord
from src.models.spec import ClarifyQuestion
from src.services import auth
from src.services.cost import usage_breakdown
from src.services.export import export_zip
from src.services.input_gate import precheck
from src.services.jobs import JobLimitError, get_jobs
from src.services.store import get_store

router = APIRouter(prefix="/runs", tags=["runs"])
SPEC_FIELDS = (
    "target", "mode", "mode_reason", "grain", "output_columns", "metrics", "filters", "assumptions", "plan_summary", "plan",
)  # fmt: skip


@router.get("", response_model=list[RunRecord])
def list_runs(user: LoggedIn, limit: int = Query(default=20, ge=1, le=100)) -> list[RunRecord]:
    """Danh sách lần chạy mới nhất mà bạn được xem (Engineer chỉ thấy lần chạy của mình hoặc dùng nguồn bạn được thấy)."""
    runs = get_store().list_runs(limit)
    if user.role in ("reviewer", "admin"):
        return runs
    visible = visible_table_names(user)
    return [r for r in runs if run_visible_to(user, r, visible)]


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def create_run(body: CreateRunBody, user: Engineer, request: Request) -> Accepted:
    """Tạo yêu cầu mới; agent chạy nền tới điểm dừng đầu tiên (câu hỏi làm rõ hoặc bản duyệt)."""
    # Cửa kiểm tra đầu vào, tầng 0–1 (0 token): bị chặn thì không tạo lần chạy, không tính hạn mức.
    # `unclear` đi tiếp: tầng 2 (model nhỏ) quyết định trong graph.
    gate = precheck(body.request_text, requester=user.name)
    if gate.status == "rejected":
        raise HTTPException(status_code=422, detail=gate.message)
    _check_limits(user.name)  # trước khi tạo: bị chặn thì không để lại lần chạy treo
    run_id = runner.create_run(body.request_text.strip(), user.name)
    auth.audit("run.create", user.name, target=run_id, ip=client_ip(request))
    get_jobs().submit(run_id, lambda sink: runner.run_created(run_id, sink), actor=user.name, owner=user.name)
    return Accepted(run_id=run_id, status="running", message="Đã nhận yêu cầu, agent đang chạy.")


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str, user: LoggedIn) -> RunDetail:
    """Trạng thái, câu hỏi đang chờ, tiến trình từng bước, đặc tả, bằng chứng, báo cáo tối ưu."""
    record = run_for_user(run_id, user)
    jobs = get_jobs()
    values = runner.get_values(run_id)
    spec = values.get("spec", {})
    busy = jobs.busy(run_id)
    pending = None if busy else runner.pending_interrupt(run_id)
    events = jobs.events(run_id)
    current = jobs.current(run_id) if busy else None
    if current:
        current["stage"] = stage_of(current["node"])
    return RunDetail(
        record=record,
        busy=busy,
        pending=pending,
        events=events,
        spec={
            **{k: spec.get(k) for k in SPEC_FIELDS},
            "sources": [{"name": s.get("name"), "kind": s.get("kind")} for s in spec.get("sources", [])],  # bỏ path
        },
        answered=values.get("answered", []),
        evidence=values.get("evidence", {}),
        optimization=values.get("optimization", {}),
        sandbox=values.get("sandbox", {}),
        code_notes=values.get("code_notes", []),
        test_notes=values.get("test_notes", []),
        stages=[
            s.model_dump()
            for s in pipeline_stages(values, events, pending, str(record.status), busy, (current or {}).get("node"))
        ],
        usage=usage_breakdown(values.get("llm_usage", [])),
        current=current,
        queue_position=jobs.position(run_id) if busy else None,
        schema_report=values.get("schema_report", {}),
        schema_decision=values.get("schema_decision", {}),
        value_filters=values.get("value_filters", []),
        reconciliation=values.get("reconciliation", []),
        retryable=not busy and str(record.status) == "failed" and not runner.retry_problem(run_id),
    )


@router.get("/{run_id}/files", response_model=RunFiles)
def get_files(run_id: str, user: LoggedIn) -> RunFiles:
    """Code + test hiện tại và bộ file vòng trước (để xem diff)."""
    run_for_user(run_id, user)
    values = runner.get_values(run_id)
    return RunFiles(
        code_files=values.get("code_files", {}),
        test_files=values.get("test_files", {}),
        previous_files=values.get("previous_files", {}),
    )


@router.get("/{run_id}/download", response_class=Response)
def download(run_id: str, user: LoggedIn) -> Response:
    """Gói zip code dbt + test + DAG (không kèm dữ liệu sandbox) để DE đưa vào repo và mở PR."""
    run_for_user(run_id, user)
    workspace = runner.get_values(run_id).get("workspace")
    if not workspace or not Path(workspace).exists():
        raise HTTPException(status_code=409, detail="Lần chạy chưa sinh code nên chưa có gì để tải.")
    name = f"p113-{run_id}"
    headers = {"Content-Disposition": f'attachment; filename="{name}.zip"'}
    return Response(export_zip(Path(workspace), name), media_type="application/zip", headers=headers)


def _pending(run_id: str, kind: str) -> dict:
    """Lần chạy phải rảnh và đang chờ đúng bước; nếu không → 409."""
    if get_jobs().busy(run_id):
        raise HTTPException(status_code=409, detail="Lần chạy đang chạy, vui lòng đợi.")
    try:
        return runner.check_resumable(run_id, kind)
    except RunStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _check_limits(owner: str, run_id: str = "") -> None:
    """Mục 14.2-14.3: quá số lần chạy cùng lúc hoặc chạm trần chi phí hôm nay → 429 kèm lý do tiếng Việt."""
    try:
        get_jobs().check(owner, run_id)
    except JobLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc


def _resume(run_id: str, kind: str, value: dict, user: CurrentUser) -> Accepted:
    owner = run_or_404(run_id).requester  # giới hạn tính cho người tạo yêu cầu, kể cả khi Reviewer bấm duyệt
    _check_limits(owner, run_id)
    request = ResumeRequest(run_id=run_id, kind=kind, value=value)
    get_jobs().submit(run_id, lambda sink: runner.resume_run(request, sink), actor=user.name, owner=owner)
    return Accepted(run_id=run_id, status="running", message="Đã nhận, agent chạy tiếp.")


@router.post("/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def retry(run_id: str, user: Engineer, request: Request) -> Accepted:
    """Chạy lại từ bước lỗi: các bước đã xong giữ nguyên, chỉ làm lại bước đang dở (xem runner.retry_problem)."""
    record = run_for_user(run_id, user)
    if get_jobs().busy(run_id):
        raise HTTPException(status_code=409, detail="Lần chạy đang chạy, vui lòng đợi.")
    problem = runner.retry_problem(run_id)
    if problem:
        raise HTTPException(status_code=409, detail=problem)
    _check_limits(record.requester, run_id)
    auth.audit("run.retry", user.name, target=run_id, ip=client_ip(request))
    get_jobs().submit(run_id, lambda sink: runner.retry_run(run_id, sink), actor=user.name, owner=record.requester)
    return Accepted(run_id=run_id, status="running", message="Đã nhận, agent chạy lại từ bước lỗi.")


@router.post("/{run_id}/answers", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def answer(run_id: str, body: AnswerBody, user: Engineer) -> Accepted:
    """Trả lời câu hỏi làm rõ (J1); lựa chọn phải đúng một trong các đáp án đã đưa ra."""
    run_for_user(run_id, user)
    questions = [ClarifyQuestion.model_validate(q) for q in _pending(run_id, "clarify").get("questions", [])]
    if len(valid_answers(questions, {"answers": body.answers})) != len(questions):
        raise HTTPException(status_code=422, detail="Cần chọn đáp án có sẵn cho mỗi câu hỏi.")
    return _resume(run_id, "clarify", {"answers": body.answers}, user)  # J1 tự kiểm và định dạng lại


@router.post("/{run_id}/input", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def add_input(run_id: str, body: InputBody, user: Engineer, request: Request) -> Accepted:
    """Cửa kiểm tra đầu vào hỏi bổ sung hoặc xin viết lại yêu cầu: gửi thêm thông tin hoặc dừng."""
    run_for_user(run_id, user)
    _pending(run_id, "input")
    if body.action == "send" and not body.text.strip():
        raise HTTPException(status_code=422, detail="Hãy nhập thông tin bổ sung hoặc câu yêu cầu viết lại.")
    auth.audit(f"input.{body.action}", user.name, target=run_id, ip=client_ip(request))
    return _resume(run_id, "input", {"action": body.action, "text": body.text.strip()}, user)


@router.post("/{run_id}/plan", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def review_plan(run_id: str, body: PlanBody, user: Engineer, request: Request) -> Accepted:
    """Duyệt kế hoạch (J1b): đồng ý → agent sinh code; sửa (kèm ghi chú) → agent lập lại kế hoạch."""
    run_for_user(run_id, user)
    _pending(run_id, "plan")
    if body.decision == "revise" and not body.note.strip():
        raise HTTPException(status_code=422, detail="Yêu cầu sửa kế hoạch thì cần ghi chú cần sửa gì.")
    auth.audit(
        f"plan.{body.decision}", user.name, target=run_id, ip=client_ip(request), detail={"options": body.options or {}}
    )
    value = {"decision": body.decision, "note": body.note.strip(), "options": body.options or {}}
    return _resume(run_id, "plan", value, user)


@router.post("/{run_id}/schema", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def confirm_schema(run_id: str, body: SchemaBody, user: Engineer, request: Request) -> Accepted:
    """Nguồn có cột bị xóa/nghi đổi tên: Engineer xác nhận cặp đổi tên (không tự đoán) rồi chạy tiếp, hoặc dừng."""
    run_for_user(run_id, user)
    _pending(run_id, "schema")
    detail = {"action": body.action, "renames": body.renames}
    auth.audit("schema.confirm", user.name, target=run_id, ip=client_ip(request), detail=detail)
    return _resume(run_id, "schema", {**body.model_dump(), "by": user.name}, user)


@router.post("/{run_id}/rescue", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def rescue(run_id: str, body: RescueBody, user: Engineer) -> Accepted:
    """Cứu hộ khi agent sửa không được: gợi ý rồi thử lại, hoặc dừng."""
    run_for_user(run_id, user)
    _pending(run_id, "rescue")
    if body.action == "retry" and not body.hint.strip():
        raise HTTPException(status_code=422, detail="Hãy nhập gợi ý cho agent trước khi thử lại.")
    return _resume(run_id, "rescue", body.model_dump(), user)
