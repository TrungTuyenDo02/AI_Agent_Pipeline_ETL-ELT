"""Đường ống E/V/J trên web: trạng thái từng nút suy từ dữ liệu thật, không đoán."""

from src.agents.stages import pipeline_stages
from src.services.cost import usage_breakdown


def _states(stages) -> dict[str, str]:
    return {s.id: s.state for s in stages}


def _event(node: str, ok: bool = True, detail: str = "") -> dict:
    return {"node": node, "ok": ok, "detail": detail}


def test_new_run_starts_at_planner():
    states = _states(pipeline_stages({}, [], None, "running", busy=True))
    assert states["planner"] == "running" and states["review"] == "waiting"
    assert "clarify" not in states and "rescue" not in states  # nút tùy chọn chỉ hiện khi đã xảy ra


def test_waiting_plan_review_is_human_step():
    events = [_event("planner"), _event("spec_check")]
    states = _states(pipeline_stages({"spec": {"target": "x"}}, events, {"kind": "plan"}, "waiting_plan_review", False))
    assert states["planner"] == states["spec_check"] == "passed"
    assert states["plan_review"] == "human" and states["codegen"] == "waiting"


def test_clarify_shows_only_when_asked():
    pending = {"kind": "clarify", "questions": []}
    states = _states(pipeline_stages({"spec": {}}, [_event("planner")], pending, "waiting_clarification", False))
    assert states["clarify"] == "human"


def test_failed_safety_sends_running_back_to_codegen():
    events = [
        _event("planner"),
        _event("spec_check"),
        _event("codegen"),
        _event("testgen"),
        _event("safety", False, "x"),
    ]
    stages = pipeline_stages({}, events, None, "running", busy=True)
    states = _states(stages)
    assert states["safety"] == "failed" and states["codegen"] == "running"


def test_without_events_uses_saved_state():
    """Sau khi khởi động lại máy chủ, nhật ký bước mất; trạng thái lấy từ checkpoint."""
    values = {
        "spec": {"target": "x"},
        "plan_review": {"decision": "approve"},
        "workspace": "w",
        "profile": {"a": {}},
        "code_files": {"a.sql": ""},
        "test_files": {"t.sql": ""},
        "safety": {"passed": True},
        "sandbox": {"passed": True},
        "optimization": {"decision": "skipped"},
    }
    states = _states(pipeline_stages(values, [], {"kind": "review"}, "waiting_review", False))
    assert all(states[k] == "passed" for k in ("planner", "spec_check", "plan_review", "sandbox", "compare"))
    assert states["review"] == "human"


def test_failed_run_without_failed_node_marks_first_open_stage():
    states = _states(pipeline_stages({"spec": {"t": 1}}, [], None, "failed", False))
    assert states["spec_check"] == "failed" and states["codegen"] == "waiting"


def test_usage_breakdown_groups_by_task_and_reports_cache():
    usages = [
        {"task": "planner", "input_tokens": 1000, "output_tokens": 200, "cached_tokens": 500, "cost_usd": 0.001,
         "latency_ms": 1500},
        {"task": "planner", "input_tokens": 1000, "output_tokens": 100, "cached_tokens": 0, "cost_usd": 0.002,
         "latency_ms": 500},
        {"task": "codegen", "input_tokens": 2000, "output_tokens": 900, "cost_usd": 0.004, "latency_ms": 3000},
    ]  # fmt: skip
    report = usage_breakdown(usages)
    planner = report["rows"][0]
    assert planner["calls"] == 2 and planner["input_tokens"] == 2000 and planner["seconds"] == 2.0
    assert planner["cost_usd"] == 0.003 and report["cache_hit_rate"] == 0.125 and not report["simulated"]


def test_usage_breakdown_mock_has_no_cache_rate():
    report = usage_breakdown([{"task": "planner", "input_tokens": 10, "simulated": True}])
    assert report["simulated"] and report["cache_hit_rate"] is None


def test_usage_breakdown_lists_models_that_actually_answered():
    usages = [
        {"task": "optimizer", "provider": "anthropic", "model": "claude-haiku-5-5", "input_tokens": 10},
        {"task": "optimizer", "provider": "google", "model": "gemini-3.1-flash-lite", "input_tokens": 10},  # dự phòng
        {"task": "optimizer", "provider": "google", "model": "gemini-3.1-flash-lite", "input_tokens": 10},
    ]
    row = usage_breakdown(usages)["rows"][0]
    assert row["models"] == ["anthropic/claude-haiku-5-5", "google/gemini-3.1-flash-lite"]
