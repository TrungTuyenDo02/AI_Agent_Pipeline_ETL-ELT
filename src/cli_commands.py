"""Xử lý từng lệnh CLI. Mỗi hàm trả mã thoát (0 = thành công)."""

import argparse
import csv
import getpass
import secrets
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from rich.prompt import Prompt

from src.agents import runner
from src.agents.runner import PermissionDeniedError, ResumeRequest, RunOutcome, RunStateError
from src.agents.tools.duckdb_tools import discover_sources
from src.cli_views import (
    STATUS_TEXT,
    ask_clarification,
    ask_plan,
    ask_rescue,
    console,
    print_doctor,
    print_errors,
    print_event,
    print_optimization,
    print_review_package,
    print_run,
    print_runs,
    show_plan,
    simulated_banner,
)
from src.config import get_settings
from src.models.evidence import ReviewDecision
from src.services import auth
from src.services.doctor import run_checks
from src.services.error_memory import get_error_memory
from src.services.llm import LLMCallError, LLMConfigError
from src.services.schema_watch import SchemaReport
from src.services.seed import SeedConfig, generate_sources
from src.services.store import get_store

AUTO_REVIEWER = "auto-reviewer"


def cmd_doctor(args: argparse.Namespace) -> int:
    """Kiểm tra môi trường."""
    results = run_checks()
    print_doctor(results)
    return 1 if any(r.level == "fail" for r in results) else 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Sinh dữ liệu giả lập."""
    settings = get_settings()
    cfg = SeedConfig(
        out_dir=settings.sources_dir,
        seed=settings.seed,
        dirty=args.dirty,
        rows_per_source=args.rows,
        profile=args.profile,
        scale=args.scale,
    )
    for name, count in generate_sources(cfg).items():
        console.print(f" [green]✓[/] {settings.sources_dir / name}" + (f": {count} dòng" if count >= 0 else ""))
    tables = len(discover_sources(settings.sources_dir))
    console.print(
        f"Tổng cộng {tables} bảng nguồn. Xem cấu trúc: màn 'Dữ liệu nguồn' trên web hoặc docs/data-catalog.md"
    )
    return 0


def _auto_review(outcome: RunOutcome) -> RunOutcome:
    console.print("[yellow]--auto-approve: tự duyệt (chỉ dùng cho test/eval).[/]")
    decision = ReviewDecision(run_id=outcome.run_id, reviewer=AUTO_REVIEWER, decision="approve", note="auto")
    return runner.submit_review(decision, "reviewer", print_event)


def _step(outcome: RunOutcome, args: argparse.Namespace) -> RunOutcome | None:
    """Xử lý một điểm dừng; trả None khi cần dừng vòng lặp."""
    kind = (outcome.pending or {}).get("kind")
    auto = getattr(args, "auto_answer", False) or getattr(args, "auto_approve", False)
    if kind == "clarify":
        answers = (
            {q["id"]: q["options"][0] for q in outcome.pending["questions"]}
            if auto
            else ask_clarification(outcome.pending)
        )
        return runner.resume_run(
            ResumeRequest(run_id=outcome.run_id, kind="clarify", value={"answers": answers}), print_event
        )
    if kind == "plan":
        if auto:
            show_plan(outcome.pending)
        value = {"decision": "approve"} if auto else ask_plan(outcome.pending)
        return runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="plan", value=value), print_event)
    if kind == "rescue":
        value = {"action": "abort"} if auto else ask_rescue(outcome.pending)
        return runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="rescue", value=value), print_event)
    if kind == "schema":  # nguồn có cột bị xóa/đổi tên: đổi tên chỉ xác nhận trên web; ở đây chạy tiếp hoặc dừng
        console.print(
            f"[yellow]Cấu trúc nguồn thay đổi: {SchemaReport.model_validate(outcome.pending['report']).summary()}[/]"
        )
        go = auto or Prompt.ask("Chạy tiếp?", choices=["continue", "abort"], default="abort") == "continue"
        value = {"action": "continue" if go else "abort", "by": args.user}
        return runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="schema", value=value), print_event)
    if kind == "review" and getattr(args, "auto_approve", False):
        return _auto_review(outcome)
    return None


def _drive(outcome: RunOutcome, args: argparse.Namespace) -> int:
    while outcome.pending:
        next_outcome = _step(outcome, args)
        if next_outcome is None:
            break
        outcome = next_outcome
    console.print(
        f"\n[bold]Trạng thái:[/] {STATUS_TEXT.get(outcome.status, outcome.status)} (run_id: {outcome.run_id})"
    )
    if outcome.error:
        console.print(f"[red]{outcome.error}[/]")
    if outcome.status == "waiting_review":
        console.print(f"Xem bằng chứng và duyệt: [bold]python -m src.cli review {outcome.run_id} --user <tên>[/]")
    return 1 if outcome.status == "failed" else 0


def cmd_run(args: argparse.Namespace) -> int:
    """Chạy luồng từ đầu, hỏi J1 ngay trong terminal."""
    if args.role != "engineer":
        console.print("[red]Chỉ vai trò Engineer tạo yêu cầu (--as engineer).[/]")
        return 2
    if get_settings().is_mock:
        simulated_banner()
    auth.audit("run.create", args.user, detail={"via": "cli"})
    try:
        return _drive(runner.start_run(args.request, args.user, print_event), args)
    except (LLMConfigError, LLMCallError, RunStateError, PermissionDeniedError) as exc:
        console.print(f"[red]{exc}[/]")
        return 1


def cmd_answer(args: argparse.Namespace) -> int:
    """Trả lời câu hỏi làm rõ cho lần chạy đang chờ J1."""
    pending = runner.pending_interrupt(args.run_id)
    if not pending or pending.get("kind") != "clarify":
        console.print("[red]Lần chạy này không chờ câu trả lời làm rõ.[/]")
        return 1
    outcome = runner.resume_run(
        ResumeRequest(run_id=args.run_id, kind="clarify", value={"answers": ask_clarification(pending)}), print_event
    )
    return _drive(outcome, args)


def _review_choice(args: argparse.Namespace) -> tuple[str, str]:
    if args.approve or args.reject:
        return ("approve" if args.approve else "reject"), args.note
    choice = Prompt.ask("Quyết định", choices=["approve", "reject", "skip"], default="skip")
    note = Prompt.ask("Ghi chú cho Coder (bắt buộc khi từ chối)") if choice == "reject" else ""
    return choice, note


def _check_reviewer(args: argparse.Namespace) -> str:
    record = get_store().get_run(args.run_id)
    if record is None:
        return f"Không tìm thấy lần chạy {args.run_id}."
    return runner.review_permission_error(args.role)


def _resolve_run_id(run_id: str) -> str:
    """`latest` = lần chạy mới nhất đang chờ duyệt."""
    if run_id != "latest":
        return run_id
    waiting = [r for r in get_store().list_runs(50) if r.status == "waiting_review"]
    return waiting[0].id if waiting else run_id


def cmd_review(args: argparse.Namespace) -> int:
    """Hiện gói duyệt rồi approve/reject (`run_id` có thể là `latest`)."""
    args.run_id = _resolve_run_id(args.run_id)
    problem = _check_reviewer(args)
    if problem:
        console.print(f"[red]{problem}[/]")
        return 2
    print_review_package(runner.get_values(args.run_id), full=args.full)
    if (runner.pending_interrupt(args.run_id) or {}).get("kind") != "review":
        console.print("[yellow]Lần chạy này không ở bước chờ duyệt.[/]")
        return 1
    decision, note = _review_choice(args)
    if decision == "skip":
        return 0
    try:
        review = ReviewDecision(run_id=args.run_id, reviewer=args.user, decision=decision, note=note)
        auth.audit(f"review.{decision}", args.user, target=args.run_id, detail={"via": "cli"})
        return _drive(runner.submit_review(review, args.role, print_event), args)
    except (PermissionDeniedError, RunStateError, LLMConfigError, LLMCallError) as exc:
        console.print(f"[red]{exc}[/]")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Danh sách lần chạy hoặc chi tiết một lần."""
    store = get_store()
    if not args.run_id:
        print_runs(store.list_runs())
        return 0
    record = store.get_run(args.run_id)
    if record is None:
        console.print(f"[red]Không tìm thấy lần chạy {args.run_id}.[/]")
        return 1
    print_run(record)
    return 0


def cmd_errors(args: argparse.Namespace) -> int:
    """Sổ lỗi: liệt kê, duyệt, bỏ (chỉ Reviewer được duyệt/bỏ)."""
    memory = get_error_memory()
    if (args.approve or args.discard) and args.role != "reviewer":
        console.print("[red]Chỉ Reviewer được duyệt hoặc bỏ mục sổ lỗi (--as reviewer).[/]")
        return 2
    if args.approve:
        ok = memory.approve(args.approve, args.fix)
        console.print(f"[green]Đã duyệt mục {args.approve}.[/]" if ok else "[red]Không có mục này.[/]")
    elif args.discard:
        ok = memory.discard(args.discard)
        console.print(f"[green]Đã bỏ mục {args.discard}.[/]" if ok else "[red]Không có mục này.[/]")
    print_errors(memory.pending())
    return 0


def _datasets_for(run_id: str | None) -> dict[str, str]:
    runs = [get_store().get_run(run_id)] if run_id else get_store().list_runs(50)
    for record in runs:
        folder = Path(record.summary.get("workspace") or "") / "datasets" if record else None
        if folder and folder.exists():
            return {p.stem: str(p) for p in folder.glob("*.duckdb")}
    return {}


def cmd_optimize(args: argparse.Namespace) -> int:
    """Chạy riêng E4 + V3 trên bộ dữ liệu thử của một lần chạy."""
    from src.agents.nodes.optimizer import OptimizeJob, optimize_standalone
    from src.agents.tools.sql_tools import SqlCheckError

    datasets = _datasets_for(args.run_id)
    if args.dataset not in datasets:
        console.print("[red]Chưa có bộ dữ liệu thử. Chạy `run` một lần trước (hoặc chỉ định --run).[/]")
        return 1
    if get_settings().is_mock:
        simulated_banner()
    try:
        job = OptimizeJob(
            sql=args.sql.read_text(encoding="utf-8").strip().rstrip(";"), datasets=datasets, bench=args.dataset
        )
        report, _ = optimize_standalone(job)
    except (OSError, SqlCheckError, LLMConfigError, LLMCallError) as exc:
        console.print(f"[red]{exc}[/]")
        return 1
    print_optimization(report.model_dump())
    for check in report.equivalence:
        console.print(f" {'[green]✓[/]' if check.equal else '[red]✗[/]'} {check.dataset}: {check.detail}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """Chạy eval/run_eval.py (tiến trình con, cùng provider đã chọn)."""
    script = Path(__file__).resolve().parents[1] / "eval" / "run_eval.py"
    command = [sys.executable, str(script), *(["--with-llm"] if args.with_llm else [])]
    if args.with_llm and get_settings().is_mock:
        simulated_banner()
    return subprocess.run(command, cwd=script.parents[1], check=False).returncode


def cmd_eval_verifiers(args: argparse.Namespace) -> int:
    """Chạy eval/verifier_bench/run_bench.py (tiến trình con; không gọi LLM)."""
    script = Path(__file__).resolve().parents[1] / "eval" / "verifier_bench" / "run_bench.py"
    command = [sys.executable, str(script), *(["--quick"] if args.quick else [])]
    return subprocess.run(command, cwd=script.parents[2], check=False).returncode


DEV_ACCOUNTS = (
    ("an", "An (Engineer)", "engineer"),
    ("binh", "Bình (Reviewer)", "reviewer"),
    ("quantri", "Quản trị", "admin"),
)


def _seed_dev_users() -> int:
    """Tài khoản mẫu cho dev: mật khẩu ngẫu nhiên in MỘT lần ra màn hình, không ghi vào file hay Git."""
    if get_settings().app_env == "production":
        console.print("[red]Không tạo tài khoản mẫu trên production.[/]")
        return 2
    for username, name, role in DEV_ACCOUNTS:
        if auth.find_user(username):
            console.print(f" [yellow]•[/] {username} đã có, bỏ qua")
            continue
        password = secrets.token_urlsafe(12)
        auth.create_user(username, name, role, password)
        console.print(f" [green]✓[/] {username} ({role}) mật khẩu: [bold]{password}[/]")
    console.print(
        "[dim]Mật khẩu chỉ hiện lần này. Quên thì: python -m src.cli users lock/unlock hoặc Admin đặt lại.[/]"
    )
    return 0


def _bulk_create_users(prefix: str, mix: str, out: str) -> int:
    """Tạo hàng loạt tài khoản thử với mật khẩu ngẫu nhiên; ghi CSV cục bộ. Tên đã có thì bỏ qua (chạy lại không trùng)."""
    try:
        engineers, reviewers, admins = (int(part) for part in mix.split("/"))
    except ValueError:
        console.print("[red]--mix phải có dạng Engineer/Reviewer/Admin, ví dụ 14/5/1.[/]")
        return 2
    roles = ["engineer"] * engineers + ["reviewer"] * reviewers + ["admin"] * admins
    width = max(2, len(str(len(roles))))
    rows: list[tuple[str, str, str]] = []
    for index, role in enumerate(roles, start=1):
        username = f"{prefix}{index:0{width}d}"
        if auth.find_user(username):
            console.print(f" [yellow]•[/] {username} đã có, bỏ qua")
            continue
        password = secrets.token_urlsafe(12)
        try:
            user = auth.create_user(username, f"{prefix.capitalize()} {index:0{width}d} ({role})", role, password)
        except ValueError as exc:
            console.print(f"[red]{username}: {exc}[/]")
            return 2
        auth.audit("user.create", "cli", target=user.username, detail={"role": role, "via": "cli-bulk"})
        rows.append((username, role, password))
    if rows:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["username", "role", "password"])
            writer.writerows(rows)
    for username, role, password in rows:
        console.print(f" [green]✓[/] {username:<12} {role:<9} {password}", highlight=False)
    console.print(
        f"[dim]Đã tạo {len(rows)} tài khoản. Mật khẩu chỉ hiện lần này" + (f"; bản CSV: {out}[/]" if rows else "[/]")
    )
    return 0


def cmd_users(args: argparse.Namespace) -> int:
    """Tài khoản đăng nhập web (cần DATABASE_URL đã chạy migration)."""
    missing = get_settings().missing_auth_settings
    if missing:
        console.print(f"[red]Thiếu biến môi trường: {', '.join(missing)}. Điền vào .env rồi chạy lại.[/]")
        return 2
    if args.action == "seed-dev":
        return _seed_dev_users()
    if args.action == "bulk-create":
        return _bulk_create_users(args.prefix, args.mix, args.out)
    if args.action == "list":
        for user in auth.list_users():
            state = "" if user.is_active else " [red](đã khóa)[/]"
            console.print(f" {user.username:<16} {user.role:<9} {user.display_name}{state}")
        return 0
    if not args.username:
        console.print("[red]Cần --username.[/]")
        return 2
    if args.action == "create":
        password = getpass.getpass("Mật khẩu (ít nhất 12 ký tự): ")
        if password != getpass.getpass("Nhập lại: "):
            console.print("[red]Hai lần nhập không khớp.[/]")
            return 2
        try:
            user = auth.create_user(args.username, args.name, args.role, password)
        except ValueError as exc:
            console.print(f"[red]{exc}[/]")
            return 2
        auth.audit("user.create", "cli", target=user.username, detail={"role": user.role, "via": "cli"})
        console.print(f"[green]Đã tạo {user.username} ({user.role}).[/]")
        return 0
    user = auth.find_user(args.username)
    if user is None:
        console.print(f"[red]Không có tài khoản {args.username}.[/]")
        return 1
    auth.update_user(user.id, is_active=args.action == "unlock")
    auth.audit(f"user.{args.action}", "cli", target=user.username, detail={"via": "cli"})
    console.print(f"[green]Đã {'mở khóa' if args.action == 'unlock' else 'khóa'} {user.username}.[/]")
    return 0


COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "doctor": cmd_doctor,
    "seed": cmd_seed,
    "run": cmd_run,
    "answer": cmd_answer,
    "review": cmd_review,
    "status": cmd_status,
    "errors": cmd_errors,
    "optimize": cmd_optimize,
    "eval": cmd_eval,
    "eval-verifiers": cmd_eval_verifiers,
    "users": cmd_users,
}
