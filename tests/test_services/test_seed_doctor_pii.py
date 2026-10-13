"""Test sinh dữ liệu giả lập, doctor, che PII, chọn ELT/ETL."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from src.agents.tools.pii import mask_rows, mask_text
from src.config import Settings, get_settings
from src.models.spec import ModeSignals, PipelineMode, SourceRef, decide_mode, signals_from_sources
from src.services import doctor
from src.services.seed import SeedConfig, generate_sources


def test_seed_is_deterministic_and_dirty(tmp_path: Path):
    first = generate_sources(SeedConfig(out_dir=tmp_path / "a", seed=7, dirty=0.1, rows_per_source=50))
    generate_sources(SeedConfig(out_dir=tmp_path / "b", seed=7, dirty=0.1, rows_per_source=50))
    csv_a = (tmp_path / "a" / "shopee_orders.csv").read_text(encoding="utf-8")
    assert csv_a == (tmp_path / "b" / "shopee_orders.csv").read_text(encoding="utf-8")
    assert first["shopee_orders.csv"] == 55  # 50 đơn + 10% dòng trùng
    assert any("." in line.split(",")[-1] for line in csv_a.splitlines()[1:])  # tiền dạng 1.075.000
    tiki = json.loads((tmp_path / "a" / "tiki_orders.json").read_text(encoding="utf-8"))
    assert {"id", "created_at", "state", "grand_total"} <= set(tiki[0])
    with closing(sqlite3.connect(tmp_path / "a" / "website.sqlite")) as conn:
        assert conn.execute("SELECT count(*) FROM orders").fetchone()[0] == 50


def test_mask_pii():
    assert mask_text("liên hệ khach12@example.com") == "liên hệ k***@example.com"
    assert mask_text("0912345678") == "091******78"
    assert mask_text("0320.958027") == "032******27"  # có dấu ngăn: trước đây lọt qua bộ che
    assert mask_text("SĐT 091 234 5678, 0912-345-678") == "SĐT 091******78, 091******78"
    assert mask_text("+84 912 345 678") == "+8491******78"
    assert mask_text("1.075.000") == "1.075.000" and mask_text("09/09/2026 11:45:00") == "09/09/2026 11:45:00"
    assert mask_rows([{"a": "x@y.com", "b": 1}]) == [{"a": "x***@y.com", "b": 1}]


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        (ModeSignals(), PipelineMode.ELT),
        (ModeSignals(restricted_pii=True), PipelineMode.ETL),
        (ModeSignals(small_subset_of_large=True), PipelineMode.ETL),
        (ModeSignals(non_tabular_source=True, tabular_source=False), PipelineMode.ETL),
        (ModeSignals(non_tabular_source=True, tabular_source=True), PipelineMode.HYBRID),
    ],
)
def test_decide_mode(signals: ModeSignals, expected: PipelineMode):
    mode, reason = decide_mode(signals)
    assert mode == expected and reason


def test_signals_from_sources_recomputed_by_code():
    sources = [SourceRef(name="a", kind="csv"), SourceRef(name="hoa_don", kind="pdf")]
    signals = signals_from_sources(sources, ModeSignals(non_tabular_source=False))
    assert signals.non_tabular_source and signals.tabular_source


def test_doctor_in_mock_mode_has_no_failures():
    results = doctor.run_checks()
    llm = next(r for r in results if r.name == "LLM")
    assert llm.level == "info" and "mock" in llm.message
    assert not [r for r in results if r.level == "fail"]


def test_doctor_reports_missing_openai_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(doctor, "get_settings", lambda: Settings(llm_provider="openai", openai_api_key=""))
    llm = next(r for r in doctor.run_checks() if r.name == "LLM")
    assert llm.level == "fail" and "OPENAI_API_KEY" in llm.message
    assert get_settings().llm_provider == "mock"


def test_doctor_database_names_neon_without_leaking_secrets(monkeypatch: pytest.MonkeyPatch):
    """Dòng "Cơ sở dữ liệu" chỉ nói loại máy chủ + database; không in mật khẩu hay chuỗi kết nối."""
    from src.services import auth

    url = "postgresql+psycopg://p113_app:MatKhauBiMat123@ep-x-pooler.ap-southeast-1.aws.neon.tech/p113?sslmode=require"
    settings = Settings(database_url=url, session_secret="s" * 40)
    monkeypatch.setattr(doctor, "get_settings", lambda: settings)
    for reachable, level in ((True, "ok"), (False, "fail")):
        monkeypatch.setattr(auth, "ping", lambda reachable=reachable: reachable)
        row = next(r for r in doctor.run_checks() if r.name == "Cơ sở dữ liệu")
        assert row.level == level and "Neon, database p113" in row.message
        assert "MatKhauBiMat123" not in row.message and "p113_app" not in row.message


def test_ensure_demo_sources_only_when_empty(tmp_path: Path):
    from src.services.seed import ensure_demo_sources

    target = tmp_path / "sources"
    assert ensure_demo_sources(target, 42) is True
    files = sorted(p.name for p in target.iterdir())
    assert files  # đã sinh dữ liệu mẫu
    assert ensure_demo_sources(target, 42) is False  # có dữ liệu rồi thì không ghi đè
    assert sorted(p.name for p in target.iterdir()) == files


def test_mask_literals_keeps_shape_not_values():
    """CLAUDE.md 2.3: lỗi gửi LLM chỉ còn hình dạng giá trị; câu SQL in lại và chuỗi định dạng `%` giữ nguyên."""
    from src.agents.tools.pii import mask_literals

    error = (
        "Conversion Error: Could not convert string 'Nguyễn Văn A' to INT32\n"
        "Could not parse string '25/13/2026' according to format specifier '%d/%m/%Y'\n"
        "LINE 12: where status = 'completed'"
    )
    assert mask_literals(error) == (
        "Conversion Error: Could not convert string 'Aaaaaa Aaa A' to INT32\n"
        "Could not parse string '99/99/9999' according to format specifier '%d/%m/%Y'\n"
        "LINE 12: where status = 'completed'"
    )


def test_codegen_prompt_gets_masked_error():
    from src.agents.nodes.codegen import codegen_variables

    state = {"sandbox": {"passed": False, "error": "Could not convert string 'an@x.vn' to INT32"}, "code_files": {}}
    assert codegen_variables(state)["last_error"] == "Could not convert string 'aa@a.aa' to INT32"
