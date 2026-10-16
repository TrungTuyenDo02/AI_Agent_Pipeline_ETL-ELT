"""Tiến trình khi chờ LLM: sự kiện "node bắt đầu" thật, thời gian đo thật, mô tả việc đang làm ghép từ state thật."""

import json
import time
from pathlib import Path

from src.agents import runner
from src.agents.activity import activity_for
from src.agents.progress import NodeStart, StepEvent, node_started
from src.agents.stages import pipeline_stages
from src.services.jobs import TIMING_MIN_SAMPLES, JobQueue, NodeTimings

STATE = {
    "request_text": "Gộp đơn hàng 3 nguồn, tính doanh thu ngày",
    "source_catalog": [{"name": "shopee_orders"}, {"name": "tiki_orders"}, {"name": "web_orders"}],
    "spec": {
        "target": "daily_revenue",
        "grain": ["order_date"],
        "output_columns": [{"name": "order_date"}, {"name": "revenue"}],
        "metrics": [{"name": "revenue"}],
        "sources": [{"name": "shopee_orders"}, {"name": "tiki_orders"}, {"name": "web_orders"}],
    },
}


def test_activity_is_built_from_real_state():
    planner = activity_for("planner", STATE)
    assert "Gộp đơn hàng 3 nguồn" in planner[0]
    assert any("3 bảng nguồn: shopee_orders, tiki_orders, web_orders" in line for line in planner)
    codegen = activity_for("codegen", STATE)
    assert any("`daily_revenue` với 2 cột: order_date, revenue" in line for line in codegen)
    assert not any("Sửa lỗi" in line for line in codegen)  # vòng đầu: không có lỗi để sửa


def test_activity_mentions_the_error_being_fixed():
    state = {**STATE, "sandbox": {"passed": False, "error": "Binder Error: cột x\nchi tiết"}, "fix_attempts": 2}
    assert activity_for("codegen", state)[0] == "Sửa lỗi lần 2: “Binder Error: cột x”"


def test_testgen_activity_does_not_claim_it_reads_pipeline_code():
    lines = activity_for("testgen", {**STATE, "code_files": {"a.sql": "select 1"}})
    assert "không xem code pipeline" in lines[0] and not any("Đọc code" in line for line in lines)


def test_unknown_or_empty_state_gives_no_invented_lines():
    assert activity_for("review", STATE) == []
    assert activity_for("codegen", {}) == ["Viết DAG Airflow chạy `dbt build`"]


def test_timings_need_enough_samples_and_survive_restart(tmp_path: Path):
    path = tmp_path / "timings.json"
    timings = NodeTimings(path)
    for seconds in [10.0, 30.0][: TIMING_MIN_SAMPLES - 1]:
        timings.add("codegen", seconds)
    assert timings.typical("codegen") == (None, TIMING_MIN_SAMPLES - 1)
    timings.add("codegen", 20.0)
    assert NodeTimings(path).typical("codegen") == (20.0, 3)  # trung vị, đọc lại từ file


def test_corrupt_timings_file_starts_empty(tmp_path: Path):
    path = tmp_path / "timings.json"
    path.write_text("{không phải json", encoding="utf-8")
    assert NodeTimings(path).typical("planner") == (None, 0)


def test_queue_tracks_current_node_then_records_step(tmp_path: Path):
    queue = JobQueue(tmp_path / "timings.json")
    sink = queue._record("r1")
    sink(NodeStart(node="codegen", label="E3 Sinh code", started_at=time.time() - 5, activity=["Viết model"]))
    current = queue.current("r1")
    assert current["node"] == "codegen" and current["elapsed_s"] >= 5 and current["typical_s"] is None
    assert current["activity"] == ["Viết model"]
    sink(StepEvent(node="codegen", label="E3 Sinh code", ok=True, detail="3 file", seconds=5.0, tokens=10))
    assert queue.current("r1") is None and queue.events("r1")[0]["detail"] == "3 file"
    assert json.loads((tmp_path / "timings.json").read_text(encoding="utf-8"))["codegen"][0] >= 5


def test_running_stage_follows_real_current_node():
    events = [{"node": "planner", "ok": True, "detail": ""}]
    states = {s.id: s.state for s in pipeline_stages({}, events, None, "running", True, current_node="ingest")}
    assert states["prepare"] == "running" and states["spec_check"] == "waiting"


def test_stream_emits_start_before_finish_for_each_node(built_state):
    seen: list[tuple[str, str]] = []
    runner.start_run(
        "Gộp đơn hàng 3 nguồn, tính doanh thu ngày",
        "frank",
        lambda e: seen.append(("start" if isinstance(e, NodeStart) else "done", e.node)),
    )
    assert seen[0] == ("start", "input_gate") and ("done", "input_gate") in seen  # cửa kiểm tra đứng đầu graph
    assert seen.index(("done", "input_gate")) < seen.index(("start", "planner")) and ("done", "planner") in seen
    assert seen.index(("start", "planner")) < seen.index(("done", "planner"))
    assert all(("start", node) in seen for kind, node in seen if kind == "done")


def test_node_started_uses_label_and_activity():
    event = node_started("planner", STATE)
    assert event.label == "E1 Lập kế hoạch" and event.activity and event.started_at <= time.time()
