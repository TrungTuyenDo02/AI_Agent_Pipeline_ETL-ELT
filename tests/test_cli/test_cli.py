"""Test giao diện dòng lệnh (gọi `main([...])` trực tiếp)."""

from pathlib import Path

import pytest

from src.cli import build_parser, main
from src.services.store import get_store


@pytest.mark.parametrize(
    "argv",
    [
        ["doctor"],
        ["seed"],
        ["run", "--request", "x"],
        ["answer", "r1"],
        ["review", "r1"],
        ["status"],
        ["errors"],
        ["optimize", "--sql", "a.sql"],
    ],
)
def test_parser_has_all_commands(argv: list[str]):
    assert build_parser().parse_args(argv).command == argv[0]


def test_doctor_and_seed(capsys, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    assert main(["doctor"]) == 0
    monkeypatch.setenv("SOURCES_DIR", str(tmp_path / "src"))
    assert main(["seed", "--rows", "20"]) == 0
    assert (tmp_path / "src" / "shopee_orders.csv").exists()
    out = capsys.readouterr().out.replace("\n", "")  # rich có thể xuống dòng giữa đường dẫn dài
    assert "Python" in out and "shopee_orders.csv" in out


def test_reviewer_role_cannot_create_request(capsys):
    assert main(["run", "--request", "x", "--as", "reviewer"]) == 2
    assert "Engineer" in capsys.readouterr().out


def test_status_and_errors_listing(capsys):
    record = get_store().create_run("doanh thu", "alice")
    assert main(["status"]) == 0
    assert main(["status", record.id]) == 0
    assert main(["status", "khong-co"]) == 1
    assert main(["errors"]) == 0


def test_errors_approve_needs_reviewer():
    assert main(["errors", "--approve", "1", "--as", "engineer"]) == 2


def test_review_blocks_wrong_role(capsys):
    record = get_store().create_run("doanh thu", "alice")
    assert main(["review", record.id, "--as", "engineer", "--user", "bob"]) == 2
    assert "Chỉ vai trò Reviewer" in capsys.readouterr().out


def test_review_approve_blocked_when_source_breaks_after_codegen(capsys, monkeypatch: pytest.MonkeyPatch):
    """Giống API: nguồn đổi cấu trúc kiểu breaking sau lúc sinh code thì CLI cũng không cho duyệt."""
    from datetime import UTC, datetime

    from src import cli_commands
    from src.models.drift import DriftReport, SchemaChangeView

    record = get_store().create_run("doanh thu", "alice")
    change = SchemaChangeView(
        id=0, source_id=1, source_name="shopee", table="orders", from_version=0, to_version=0, change_type="column_removed",
        severity="breaking", detail="Cột amount bị xóa", hint="", detected_at=datetime.now(UTC), status="open",
    )  # fmt: skip
    monkeypatch.setattr(cli_commands, "print_review_package", lambda values, full=False: None)
    monkeypatch.setattr(cli_commands.runner, "get_values", lambda run_id: {})
    monkeypatch.setattr(cli_commands.runner, "pending_interrupt", lambda run_id: {"kind": "review"})
    monkeypatch.setattr(
        cli_commands.schema_drift, "recheck_run", lambda values, run_id: DriftReport(open_breaking=[change])
    )
    monkeypatch.setattr(cli_commands.runner, "submit_review", lambda *a, **k: pytest.fail("không được gửi duyệt"))
    assert main(["review", record.id, "--approve", "--as", "reviewer", "--user", "bob"]) == 1
    assert "Cột amount bị xóa" in capsys.readouterr().out.replace("\n", "")


def test_users_seed_dev_prints_random_passwords_once(capsys):
    from src.services import auth

    assert main(["users", "seed-dev"]) == 0
    first = capsys.readouterr().out
    assert {"an", "binh", "quantri"} <= {u.username for u in auth.list_users()}
    assert "mật khẩu" in first
    assert main(["users", "seed-dev"]) == 0  # chạy lại: không tạo trùng, không in lại mật khẩu
    assert "bỏ qua" in capsys.readouterr().out
    assert main(["users", "lock", "--username", "an"]) == 0 and not auth.find_user("an").is_active
    assert main(["users", "unlock", "--username", "an"]) == 0 and auth.find_user("an").is_active


def test_users_bulk_create_roles_csv_and_idempotent(tmp_path: Path, capsys):
    import csv
    import uuid

    from src.services import auth

    prefix = f"t{uuid.uuid4().hex[:6]}"  # kho test (Postgres) dùng chung giữa các lần chạy: tên phải duy nhất
    out = tmp_path / "accounts.csv"
    args = ["users", "bulk-create", "--prefix", prefix, "--mix", "3/2/1", "--out", str(out)]
    assert main(args) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    assert [r["username"] for r in rows] == [f"{prefix}{n:02d}" for n in range(1, 7)]
    assert [r["role"] for r in rows] == ["engineer"] * 3 + ["reviewer"] * 2 + ["admin"]
    assert all(len(r["password"]) >= 12 for r in rows) and len({r["password"] for r in rows}) == 6
    assert auth.authenticate(f"{prefix}01", rows[0]["password"]) is not None
    capsys.readouterr()
    assert main(args) == 0  # chạy lại: không tạo trùng
    assert "bỏ qua" in capsys.readouterr().out
    assert main(["users", "bulk-create", "--mix", "abc"]) == 2


def test_optimize_without_datasets(tmp_path: Path, capsys):
    sql = tmp_path / "q.sql"
    sql.write_text("select 1", encoding="utf-8")
    assert main(["optimize", "--sql", str(sql), "--run", "khong-co"]) == 1


@pytest.mark.slow
def test_run_end_to_end_with_auto_approve(built_state, capsys):
    assert (
        main(
            [
                "--provider",
                "mock",
                "run",
                "--request",
                "Gộp đơn 3 nguồn, doanh thu ngày",
                "--user",
                "erin",
                "--auto-approve",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Chế độ mô phỏng" in out and "đã duyệt" in out
    latest = get_store().list_runs(1)[0]
    assert latest.status == "approved" and latest.requester == "erin"


def test_eval_command_is_registered():
    from src.cli import build_parser
    from src.cli_commands import COMMANDS

    args = build_parser().parse_args(["eval", "--with-llm"])
    assert args.command == "eval" and args.with_llm is True and "eval" in COMMANDS


def test_users_create_first_admin_hides_password(capsys, monkeypatch: pytest.MonkeyPatch):
    """Tạo admin đầu tiên: mật khẩu nhập ẩn (getpass), không bao giờ in ra màn hình; hai lần nhập lệch thì không tạo."""
    from src.services import auth

    secret = "mat-khau-thu-nghiem-123"
    answers = iter([secret, secret])
    monkeypatch.setattr("src.cli_commands.getpass.getpass", lambda prompt="": next(answers))
    assert main(["users", "create", "--username", "admin-dau-tien", "--name", "Admin", "--role", "admin"]) == 0
    out = capsys.readouterr()
    assert secret not in out.out + out.err
    assert auth.find_user("admin-dau-tien").role == "admin"

    mismatch = iter([secret, "khac-hoan-toan-123"])
    monkeypatch.setattr("src.cli_commands.getpass.getpass", lambda prompt="": next(mismatch))
    assert main(["users", "create", "--username", "admin-hai", "--name", "Admin", "--role", "admin"]) == 2
    assert auth.find_user("admin-hai") is None
