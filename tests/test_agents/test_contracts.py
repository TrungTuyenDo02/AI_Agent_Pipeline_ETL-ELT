"""Hợp đồng bàn giao giữa node: đúng khuôn thì giữ nguyên hình dạng dict; sai khuôn thì báo lỗi ngay."""

import pytest
from pydantic import ValidationError

from src.models.contracts import OptCandidate, PlanDecision, SafetyResult, SandboxResult, hand_off


def test_hand_off_keeps_exactly_the_given_keys():
    failed = {"passed": False, "error": "lỗi", "models_ok": 1, "models_total": 2, "tests_ok": 0, "tests_total": 3}
    assert hand_off(SandboxResult, failed) == failed  # không thêm target_rows/sample rỗng vào state
    assert hand_off(SafetyResult, {"passed": True, "issues": []}) == {"passed": True, "issues": []}


def test_unknown_field_and_wrong_type_are_rejected():
    with pytest.raises(ValidationError):
        hand_off(SafetyResult, {"passed": True, "issues": [], "extra": 1})
    with pytest.raises(ValidationError):
        hand_off(SandboxResult, {"passed": "khong", "models_ok": "x"})


def test_plan_decision_only_two_values():
    assert hand_off(PlanDecision, {"decision": "approve", "note": ""})["decision"] == "approve"
    with pytest.raises(ValidationError):
        hand_off(PlanDecision, {"decision": "maybe", "note": "x"})


def test_opt_candidate_requires_known_source_and_baseline():
    base = {"original_sql": "select 1", "before": {"median_ms": 1.0, "runs": 3}, "source": "rules", "sql": "select 1"}
    assert hand_off(OptCandidate, base)["source"] == "rules"
    with pytest.raises(ValidationError):
        hand_off(OptCandidate, {**base, "source": "bịa"})
    with pytest.raises(ValidationError):
        hand_off(OptCandidate, {"source": "llm", "sql": "x"})  # thiếu original_sql/before
