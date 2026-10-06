"""V1 red team (U3): mọi ca tấn công bị chặn, mọi ca hợp lệ được qua — chạy trong CI để ca lọt cũ không quay lại."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "verifier_bench"))

from v1_bench import load_cases, run_case  # noqa: E402

from src.agents.nodes.safety import check_sql  # noqa: E402

ATTACKS = load_cases("v1_redteam.yaml")
VALID = load_cases("v1_valid.yaml")


def test_bench_has_enough_cases():
    assert len(ATTACKS) >= 30 and len(VALID) >= 20
    assert all(c.label == "block" for c in ATTACKS) and all(c.label == "pass" for c in VALID)
    assert len({c.id for c in ATTACKS + VALID}) == len(ATTACKS) + len(VALID)


def _attack_param(case):
    """Ca `known_leak` (rủi ro chặn ở lớp khác) là xfail strict: nếu V1 bắt đầu chặn được thì test báo để gỡ nhãn."""
    marks = [pytest.mark.xfail(strict=True, reason=case.note)] if case.known_leak else []
    return pytest.param(case, id=case.id, marks=marks)


@pytest.mark.parametrize("case", [_attack_param(c) for c in ATTACKS])
def test_attack_is_blocked(case):
    result = run_case(case)
    assert result.blocked, f"V1 để lọt ca tấn công '{case.id}'"
    assert "NGOẠI LỆ" not in result.detail, f"V1 vỡ (ném ngoại lệ) thay vì báo lỗi: {result.detail}"


@pytest.mark.parametrize("case", VALID, ids=lambda c: c.id)
def test_valid_code_passes(case):
    result = run_case(case)
    assert not result.blocked, f"V1 chặn nhầm code hợp lệ '{case.id}': {result.detail}"


def test_unknown_jinja_returns_issue_instead_of_raising():
    """Trước 2026-10-05, Jinja lạ làm check_sql ném ngoại lệ → node V1 vỡ thay vì đưa lỗi cho Coder sửa."""
    issues, columns = check_sql("{{ run_query('drop table raw.orders') }}\nselect 1 as x", {"raw": {}})
    assert issues and not columns
