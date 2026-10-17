"""Chạy graph theo từng lần chạy (run_id = thread_id): bắt đầu, tạm dừng ở J1/J2/cứu hộ, chạy tiếp.

Dùng chung cho CLI và API. Trạng thái graph lưu bằng checkpointer (SQLite hoặc PostgreSQL theo STATE_BACKEND); tóm tắt lưu trong store.

Tạm dừng theo yêu cầu (ADR 0016): graph chạy TỪNG NODE MỘT (`interrupt_before="*"` lúc gọi `stream`: LangGraph lưu checkpoint
rồi dừng trước node kế tiếp). Giữa hai node, runner xem trong store có yêu cầu tạm dừng không; có thì dừng hẳn (không chạy
node kế, không gọi thêm AI, trả lại luồng nền). Node đang chạy (kể cả lời gọi LLM đã gửi) luôn được chạy xong.
Tiếp tục = chạy tiếp từ checkpoint đó với cùng run_id: node đã xong không chạy lại, kết quả đã lưu không gọi AI lại.
"""

import logging
import sqlite3
import time
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

from src.agents.graph import build_graph
from src.agents.nodes.common import remember_fixes
from src.agents.progress import NodeStart, StepEvent, describe, node_started
from src.config import get_settings
from src.models.evidence import ReviewDecision
from src.models.schemas import RunRecord, RunStatus
from src.services import auth, schema_drift
from src.services.cost_ledger import get_ledger, llm_caller
from src.services.llm import LLMCallError, LLMConfigError, run_budget
from src.services.store import VN_TZ, get_store

logger = logging.getLogger(__name__)
EventCallback = Callable[[StepEvent | NodeStart], None]  # NodeStart: node bắt đầu; StepEvent: node xong
INTERRUPT_STATUS = {
    "input": RunStatus.WAITING_INPUT,
    "clarify": RunStatus.WAITING_CLARIFICATION,
    "plan": RunStatus.WAITING_PLAN,
    "drift": RunStatus.WAITING_DRIFT,
    "schema": RunStatus.WAITING_SCHEMA,
    "rescue": RunStatus.WAITING_RESCUE,
    "review": RunStatus.WAITING_REVIEW,
}


OWNER_ONLY = "Chỉ người tạo yêu cầu mới tạm dừng hoặc tiếp tục được lần chạy này."
NOT_RUNNING = "Lần chạy không đang chạy nên không tạm dừng được (đã xong, đã dừng hoặc đang chờ người)."
RECURSION_LIMIT = (
    200  # trần số node mỗi lượt chạy (thay `recursion_limit` của LangGraph vì nay mỗi lần gọi chỉ chạy 1 node)
)
TOO_MANY_STEPS = "Lần chạy đi quá {limit} bước trong một lượt (có thể lặp vô hạn) nên dừng lại. Xem log."


class RunStateError(RuntimeError):
    """Lần chạy không ở đúng bước để thực hiện thao tác."""


class PermissionDeniedError(PermissionError):
    """Vai trò/người dùng không được phép thao tác."""


class RunOutcome(BaseModel):
    """Kết quả sau mỗi lần chạy/tiếp tục."""

    run_id: str
    status: RunStatus
    pending: dict | None = None
    error: str = ""


class ResumeRequest(BaseModel):
    """Tiếp tục một lần chạy đang chờ bước `kind` với dữ liệu `value`."""

    run_id: str
    kind: str
    value: dict


@lru_cache
def _postgres_pool() -> ConnectionPool:
    """Pool kết nối tới Neon cho checkpointer (nhiều luồng chạy cùng lúc).

    autocommit + dict_row là yêu cầu của langgraph-checkpoint-postgres. `prepare_threshold=None` tắt prepared statement
    vì host `-pooler` của Neon (PgBouncer) không giữ được chúng giữa các lần mượn kết nối. `check` thử kết nối trước khi
    đưa ra dùng, vì Neon tự ngủ sau 5 phút và làm đứt kết nối cũ.
    """
    settings = get_settings()
    url = settings.database_url.replace("postgresql+psycopg", "postgresql", 1)
    return ConnectionPool(
        url,
        min_size=1,
        max_size=settings.run_workers + 2,
        kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row, "connect_timeout": 15},
        check=ConnectionPool.check_connection,
        open=True,
    )


@lru_cache
def _graph(backend: str, checkpoint_path: str) -> CompiledStateGraph:
    if backend == "postgres":
        return build_graph(PostgresSaver(_postgres_pool()))
    conn = sqlite3.connect(checkpoint_path, check_same_thread=False)
    return build_graph(SqliteSaver(conn))


def get_graph() -> CompiledStateGraph:
    """Graph đã gắn checkpointer (SQLite: mỗi tiến trình một kết nối; PostgreSQL: pool kết nối)."""
    settings = get_settings()
    path = settings.checkpoint_path
    if settings.state_backend == "sqlite":
        path.parent.mkdir(parents=True, exist_ok=True)
    return _graph(settings.state_backend, str(path.resolve()))


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}, "recursion_limit": RECURSION_LIMIT}


class StepResult(BaseModel):
    """Kết quả một lượt chạy graph: lỗi (rỗng = không lỗi) và có dừng vì yêu cầu tạm dừng không."""

    error: str = ""
    paused: bool = False


def _stream(run_id: str, payload: object, on_event: EventCallback | None) -> StepResult:
    """Chạy graph tới điểm dừng kế tiếp (chờ người, xong, lỗi hoặc tạm dừng theo yêu cầu)."""
    used = sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in get_values(run_id).get("llm_usage", []))
    record = get_store().get_run(run_id)
    owner = record.requester if record else ""  # sổ chi phí: tiền của lượt gọi tính cho người tạo lần chạy
    with run_budget(get_settings().run_token_budget, used), llm_caller(owner, run_id):  # trần token + trần tiền
        return _consume(run_id, payload, on_event)


def _consume(run_id: str, payload: object, on_event: EventCallback | None) -> StepResult:
    """Chạy graph TỪNG NODE MỘT, phát sự kiện từng bước; giữa hai node xem có yêu cầu tạm dừng không.

    Lượt đầu mang `payload` (đầu vào mới, câu trả lời `Command(resume=…)`, hoặc None = chạy tiếp từ checkpoint). Câu trả lời
    của người dùng luôn được ghi vào graph trước (node chờ người chỉ chạy code, không gọi AI) để không mất khi tạm dừng.
    """
    graph, config, store = get_graph(), _config(run_id), get_store()
    last = time.perf_counter()
    first: object = payload
    steps = 0
    try:
        while True:
            if not isinstance(first, Command) and store.take_pause(run_id):
                return StepResult(paused=True)  # dừng TRƯỚC node kế tiếp: chưa chạy, chưa gọi AI
            for mode, chunk in graph.stream(first, config, stream_mode=["updates", "tasks"], interrupt_before="*"):
                if mode == "tasks":  # "tasks" có `input` khi node bắt đầu, có `result` khi node xong (bỏ qua)
                    if on_event and "input" in chunk and isinstance(chunk["input"], dict):
                        on_event(node_started(chunk["name"], chunk["input"]))
                    continue
                for node, update in chunk.items():
                    if node == "__interrupt__":
                        continue
                    now = time.perf_counter()
                    if on_event:
                        on_event(describe(node, update or {}, now - last))
                    last = now
            first = None
            snapshot = graph.get_state(config)
            if not snapshot.next or any(task.interrupts for task in snapshot.tasks):
                return StepResult()  # xong, hoặc tới bước chờ người: giữ trạng thái chờ, không thêm "tạm dừng"
            steps += 1
            if steps > RECURSION_LIMIT:
                return StepResult(error=TOO_MANY_STEPS.format(limit=RECURSION_LIMIT))
    except (LLMConfigError, LLMCallError) as exc:
        return StepResult(error=str(exc))
    except Exception:  # ranh giới cuối: ghi log đầy đủ, chỉ trả thông báo thân thiện
        logger.exception("graph run failed", extra={"run_id": run_id})
        return StepResult(error="Có lỗi nội bộ khi chạy pipeline. Xem log để biết chi tiết.")


def get_values(run_id: str) -> dict:
    """State hiện tại của lần chạy (rỗng nếu chưa có)."""
    return dict(get_graph().get_state(_config(run_id)).values or {})


def pending_interrupt(run_id: str) -> dict | None:
    """Câu hỏi/bước đang chờ con người (None nếu không chờ)."""
    snapshot = get_graph().get_state(_config(run_id))
    return next((i.value for task in snapshot.tasks for i in task.interrupts), None)


def summarize(values: dict, error: str) -> dict:
    """Tóm tắt lưu vào store (hiển thị danh sách, API)."""
    usage = values.get("llm_usage", [])
    report = values.get("optimization") or {}
    return {
        "target": values.get("spec", {}).get("target"),
        "mode": values.get("spec", {}).get("mode"),
        "fix_attempts": values.get("fix_attempts", 0),
        "rescue_count": values.get("rescue_count", 0),
        "review_rounds": values.get("review_rounds", 0),
        "optimization": report.get("decision"),
        "improvement_pct": report.get("improvement_pct"),
        "llm_calls": len(usage),
        "tokens": sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in usage),
        "cost_usd": round(sum(u.get("cost_usd", 0.0) for u in usage), 6),
        "simulated": any(u.get("simulated") for u in usage),
        "workspace": values.get("workspace"),
        "sources": [s.get("name") for s in values.get("spec", {}).get("sources", []) if s.get("name")],
        "error": error or values.get("error", ""),
    }


def record_dependencies(run_id: str, values: dict) -> None:
    """Pipeline dùng cột nào của nguồn nào (phân tích SQL đã sinh bằng sqlglot): để biết thay đổi cấu trúc nào làm hỏng pipeline nào."""
    try:
        used = {s.get("name") for s in values.get("spec", {}).get("sources", [])}
        catalog = [i for i in values.get("source_catalog", []) if i["name"] in used]
        schema_drift.save_dependencies(run_id, schema_drift.extract_dependencies(values.get("code_files", {}), catalog))
    except Exception:  # noqa: BLE001 — lỗi ghi phụ thuộc không được làm hỏng lần chạy
        logger.exception("pipeline dependencies not saved", extra={"run_id": run_id})


def _finish(run_id: str, result: StepResult) -> RunOutcome:
    values, pending = get_values(run_id), pending_interrupt(run_id)
    error = result.error
    if error:
        status = RunStatus.FAILED
    elif result.paused:
        status = RunStatus.PAUSED
    elif pending:
        status = INTERRUPT_STATUS.get(pending.get("kind"), RunStatus.RUNNING)
    else:
        status = RunStatus(values.get("status") or RunStatus.RUNNING)
    get_store().update_run(run_id, status, summarize(values, error))  # khác "running" → bỏ yêu cầu tạm dừng còn treo
    if status is RunStatus.PAUSED:
        record = get_store().get_run(run_id)
        auth.audit(
            "run.paused", record.requester if record else "", target=run_id, detail={"next": _next_nodes(run_id)}
        )
    if status is RunStatus.WAITING_REVIEW:
        remember_fixes(run_id, values)
        record_dependencies(run_id, values)
    return RunOutcome(run_id=run_id, status=status, pending=pending, error=error or values.get("error", ""))


def _next_nodes(run_id: str) -> list[str]:
    """Node sẽ chạy khi tiếp tục (ghi nhật ký kiểm toán; chỉ tên node, không có dữ liệu)."""
    return list(get_graph().get_state(_config(run_id)).next or [])


def _initial_payload(record: RunRecord) -> dict:
    return {"run_id": record.id, "request_text": record.request_text, "requester": record.requester, "llm_usage": []}


def create_run(request_text: str, requester: str) -> str:
    """Tạo bản ghi lần chạy (chưa chạy graph); API dùng để trả run_id ngay rồi chạy nền."""
    return get_store().create_run(request_text, requester).id


def run_created(run_id: str, on_event: EventCallback | None = None) -> RunOutcome:
    """Chạy một lần chạy vừa tạo tới điểm dừng đầu tiên."""
    record = get_store().get_run(run_id)
    if record is None:
        raise RunStateError(f"Không tìm thấy lần chạy {run_id}.")
    return _finish(run_id, _stream(run_id, _initial_payload(record), on_event))


def run_patch(run_id: str, seed: dict, on_event: EventCallback | None = None) -> RunOutcome:
    """Chạy run vá: trạng thái khởi đầu (`seed`) mang đặc tả, câu trả lời và code của lần chạy gốc nên graph vào thẳng `patch_start`."""
    record = get_store().get_run(run_id)
    if record is None:
        raise RunStateError(f"Không tìm thấy lần chạy {run_id}.")
    payload = {
        "run_id": run_id,
        "request_text": record.request_text,
        "requester": record.requester,
        "llm_usage": [],
        **seed,
    }
    return _finish(run_id, _stream(run_id, payload, on_event))


def start_run(request_text: str, requester: str, on_event: EventCallback | None = None) -> RunOutcome:
    """Tạo lần chạy mới và chạy tới điểm dừng đầu tiên."""
    return run_created(create_run(request_text, requester), on_event)


def check_resumable(run_id: str, kind: str) -> dict:
    """Lần chạy phải đang chờ đúng bước `kind`; trả về nội dung đang chờ."""
    pending = pending_interrupt(run_id)
    if not pending or pending.get("kind") != kind:
        raise RunStateError(f"Lần chạy {run_id} không ở bước chờ '{kind}'.")
    return pending


def retry_problem(run_id: str, check_status: bool = True) -> str:
    """Lý do KHÔNG chạy lại từ bước lỗi được (chuỗi rỗng = được).

    Chạy lại = tiếp tục từ checkpoint cuối: các bước đã xong giữ nguyên (không gọi lại LLM, không chạy lại sandbox), chỉ
    làm lại bước đang dở khi lỗi. Dùng cho lỗi tạm thời (LLM quá hạn/hết hạn mức, server khởi động lại giữa chừng).
    Lần chạy đã đi tới nhánh "thất bại" của graph (hết lượt sửa, bị dừng) thì không có bước nào để tiếp tục.
    """
    record = get_store().get_run(run_id)
    if record is None:
        return f"Không tìm thấy lần chạy {run_id}."
    if check_status and record.status != RunStatus.FAILED:
        return "Chỉ chạy lại được lần chạy đang ở trạng thái lỗi."
    snapshot = get_graph().get_state(_config(run_id))
    if not snapshot.next or "fail" in snapshot.next:
        return "Lần chạy đã dừng hẳn (hết lượt sửa hoặc bị dừng), không có bước nào để tiếp tục. Hãy tạo yêu cầu mới."
    return ""


def retry_run(run_id: str, on_event: EventCallback | None = None) -> RunOutcome:
    """Chạy lại từ bước lỗi (xem `retry_problem`)."""
    # API đã kiểm trạng thái FAILED trước khi xếp hàng; lúc job chạy trạng thái đã được đặt lại thành RUNNING
    problem = retry_problem(run_id, check_status=False)
    if problem:
        raise RunStateError(problem)
    get_store().update_run(run_id, RunStatus.RUNNING)
    return _finish(run_id, _stream(run_id, None, on_event))


def pause_problem(record: RunRecord, user_name: str) -> str:
    """Lý do KHÔNG tạm dừng được (chuỗi rỗng = được): chỉ người tạo yêu cầu, chỉ khi lần chạy đang chạy hoặc xếp hàng.

    Đã tạm dừng rồi (bấm lặp) cũng được: không làm gì thêm.
    """
    if record.requester != user_name:
        return OWNER_ONLY
    if record.status not in (RunStatus.RUNNING, RunStatus.PAUSED):
        return NOT_RUNNING
    return ""


def resume_problem(record: RunRecord, user_name: str) -> str:
    """Lý do KHÔNG tiếp tục được: chỉ người tạo yêu cầu, lần chạy phải đang tạm dừng, còn trần token/tiền của lần chạy."""
    if record.requester != user_name:
        return OWNER_ONLY
    if record.status != RunStatus.PAUSED:
        return "Lần chạy không ở trạng thái đã tạm dừng nên không tiếp tục được."
    return budget_problem(record.id)


def budget_problem(run_id: str) -> str:
    """Trần của riêng lần chạy (token, tiền) và trần toàn hệ thống hôm nay. Chạm trần thì không chạy tiếp, vì lượt gọi AI kế
    tiếp chắc chắn bị chặn (trần theo người và số lần chạy cùng lúc do `jobs.check_limits` kiểm)."""
    settings = get_settings()
    used = sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in get_values(run_id).get("llm_usage", []))
    if settings.run_token_budget and used >= settings.run_token_budget:
        return (
            f"Lần chạy đã dùng {used:,} token, chạm trần {settings.run_token_budget:,} token mỗi lần chạy "
            "(RUN_TOKEN_BUDGET) nên không tiếp tục được. Hãy tạo yêu cầu nhỏ hơn hoặc nhờ quản trị viên tăng trần."
        )
    ledger = get_ledger()
    if settings.run_cost_budget_usd and ledger.used_usd("run", run_id) >= settings.run_cost_budget_usd:
        return (
            f"Lần chạy đã dùng hết trần {settings.run_cost_budget_usd:.2f} USD mỗi lần chạy (RUN_COST_BUDGET_USD) "
            "nên không tiếp tục được."
        )
    day = datetime.now(VN_TZ).date().isoformat()
    if (
        settings.llm_global_daily_budget_usd
        and ledger.used_usd("global", "*", day) >= settings.llm_global_daily_budget_usd
    ):
        return "Hệ thống đã dùng hết ngân sách AI hôm nay. Hãy tiếp tục vào ngày mai hoặc liên hệ quản trị viên."
    return ""


def continue_run(run_id: str, on_event: EventCallback | None = None) -> RunOutcome:
    """Tiếp tục lần chạy đã tạm dừng từ checkpoint cuối (cùng run_id): node đã xong không chạy lại.

    Lần chạy bị tạm dừng khi còn trong hàng đợi (graph chưa nhận đầu vào) thì bắt đầu từ đầu vào ban đầu.
    """
    record = get_store().get_run(run_id)
    if record is None:
        raise RunStateError(f"Không tìm thấy lần chạy {run_id}.")
    started = get_graph().get_state(_config(run_id)).created_at is not None
    get_store().update_run(run_id, RunStatus.RUNNING)
    return _finish(run_id, _stream(run_id, None if started else _initial_payload(record), on_event))


def resume_run(request: ResumeRequest, on_event: EventCallback | None = None) -> RunOutcome:
    """Tiếp tục khi đúng bước đang chờ."""
    check_resumable(request.run_id, request.kind)
    get_store().update_run(request.run_id, RunStatus.RUNNING)
    return _finish(request.run_id, _stream(request.run_id, Command(resume=request.value), on_event))


SELF_REVIEW = "Người tạo yêu cầu không được tự duyệt hoặc từ chối. Hãy nhờ một Reviewer khác."


def review_permission_error(role: str, reviewer: str = "", requester: str = "") -> str:
    """Luật duyệt J2 (dùng chung cho CLI và API); chuỗi rỗng = được phép.

    Chỉ vai trò Reviewer được duyệt hoặc từ chối. REQUIRE_SEPARATE_REVIEWER (mặc định bật, ADR 0006 thay ADR 0004): người tạo
    yêu cầu không tự duyệt được; tắt công tắc khi chạy demo cá nhân. Không có đường tắt: Engineer/Admin đều bị chặn.
    """
    if role != "reviewer":
        return "Chỉ vai trò Reviewer mới được duyệt hoặc từ chối."
    same_person = bool(reviewer) and reviewer == requester
    return SELF_REVIEW if same_person and get_settings().require_separate_reviewer else ""


def check_review(decision: ReviewDecision, role: str) -> None:
    """Kiểm tra trước khi duyệt: lần chạy tồn tại, đúng quyền, đang chờ duyệt (lỗi → ngoại lệ)."""
    record = get_store().get_run(decision.run_id)
    if record is None:
        raise RunStateError(f"Không tìm thấy lần chạy {decision.run_id}.")
    problem = review_permission_error(role, decision.reviewer, record.requester)
    if problem:
        raise PermissionDeniedError(problem)
    check_resumable(decision.run_id, "review")


def submit_review(decision: ReviewDecision, role: str, on_event: EventCallback | None = None) -> RunOutcome:
    """J2: duyệt hoặc từ chối theo luật ở `review_permission_error`."""
    check_review(decision, role)
    value = decision.model_dump(exclude={"run_id"})
    outcome = resume_run(ResumeRequest(run_id=decision.run_id, kind="review", value=value), on_event)
    get_store().add_review(decision)
    return outcome
