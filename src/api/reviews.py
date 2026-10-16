"""Duyệt (J2): hàng đợi chờ duyệt; chỉ vai trò Reviewer được approve/reject (luật chung với CLI ở runner)."""

from fastapi import APIRouter, HTTPException, Request, status

from src.agents import runner
from src.agents.runner import PermissionDeniedError, RunStateError
from src.api.deps import FORBIDDEN, LoggedIn, Reviewer, client_ip, run_or_404, run_visible_to, visible_table_names
from src.api.requests import Accepted, ReviewBody
from src.models.evidence import ReviewDecision
from src.models.schemas import RunRecord, RunStatus
from src.services import auth, schema_drift
from src.services.jobs import JobLimitError, get_jobs
from src.services.store import get_store

router = APIRouter(tags=["reviews"])


@router.get("/reviews/queue", response_model=list[RunRecord])
def review_queue(user: LoggedIn) -> list[RunRecord]:
    """Các lần chạy đang chờ duyệt (mới nhất trước) mà bạn được xem."""
    waiting = [r for r in get_store().list_runs(100) if r.status == RunStatus.WAITING_REVIEW]
    visible = visible_table_names(user) if user.role == "engineer" else set()
    return [r for r in waiting if run_visible_to(user, r, visible)]


@router.post("/runs/{run_id}/review", status_code=status.HTTP_202_ACCEPTED, response_model=Accepted)
def review(run_id: str, body: ReviewBody, user: Reviewer, request: Request) -> Accepted:
    """Duyệt hoặc từ chối; từ chối kèm ghi chú → agent sửa lại rồi chờ duyệt lần nữa."""
    owner = run_or_404(run_id).requester
    if body.decision == "reject" and not body.note.strip():
        raise HTTPException(status_code=422, detail="Từ chối thì cần ghi chú để agent biết sửa gì.")
    if get_jobs().busy(run_id):
        raise HTTPException(status_code=409, detail="Lần chạy đang chạy, vui lòng đợi.")
    decision = ReviewDecision(run_id=run_id, reviewer=user.name, decision=body.decision, note=body.note.strip())
    try:
        runner.check_review(decision, user.role)
    except PermissionDeniedError as exc:  # vai trò đã kiểm ở require_role: còn lại là luật tách người tạo/người duyệt
        raise HTTPException(status_code=403, detail=str(exc) or FORBIDDEN) from exc
    except RunStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if (
        body.decision == "approve"
    ):  # ngay trước J2: cấu trúc nguồn đổi kiểu breaking sau lúc sinh code thì chặn nút duyệt
        report = schema_drift.recheck_run(runner.get_values(run_id), run_id)
        if report.blocked:
            what = "; ".join(c.detail for c in report.open_breaking[:3])
            raise HTTPException(status_code=409, detail=schema_drift.BLOCKED_REVIEW.format(what=what))
    if body.decision == "reject":  # từ chối → agent sửa lại (tốn LLM): tính giới hạn của người tạo yêu cầu
        try:
            get_jobs().check(owner, run_id)
        except JobLimitError as exc:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    auth.audit(f"review.{body.decision}", user.name, target=run_id, ip=client_ip(request))
    job = lambda sink: runner.submit_review(decision, user.role, sink)  # noqa: E731
    get_jobs().submit(run_id, job, actor=user.name, owner=owner)
    message = "Đã duyệt." if body.decision == "approve" else "Đã từ chối, agent đang sửa theo ghi chú."
    return Accepted(run_id=run_id, status="running", message=message)
