"""Bộ eval hiệu năng (eval/run_perf.py): so kết quả có dung sai, độ ổn định giữa các lượt, chạy thật 2 ca x 2 lượt."""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

from run_perf import load_cases, read_expected, same_rows, stability  # noqa: E402


def _row(**over) -> dict:
    base = {"id": "c", "correct": True, "bottleneck_hit": True, "decision": "skipped", "kept_result": None}
    return {**base, "before_ms": 100.0, "before_iqr_ms": 5.0, **over}


def test_same_rows_ignores_order_and_float_noise():
    assert same_rows([["b", "2.0"], ["a", "1.0"]], [["a", "1.0000000000001"], ["b", "2.0"]])
    assert not same_rows([["a", "1.0"]], [["a", "1.01"]])
    assert not same_rows([["a", "1"]], [["a", "1"], ["b", "2"]])
    assert not same_rows([["a", "1"]], None)  # chưa đóng băng đáp án: không tính là đúng


def test_stability_reports_unstable_instead_of_forcing_pass():
    assert stability([[_row()]])["checked"] is False
    assert stability([[_row()], [_row(before_ms=103.0)]])["stable"] is True  # lệch trong IQR
    drift = stability([[_row()], [_row(before_ms=130.0)]])
    assert (
        drift["stable"] is False and drift["note"] == "kết quả chưa ổn định" and "before_ms" in drift["differences"][0]
    )
    assert drift["conclusions_stable"] is True and drift["timings_stable"] is False
    widened = stability([[_row(noise_pct=40.0)], [_row(before_ms=130.0)]])  # nhiễu đo được 40 ms trong lượt đầu
    assert widened["stable"] is True
    flipped = stability([[_row()], [_row(decision="applied", kept_result=True)]])
    assert flipped["stable"] is False and "decision" in flipped["differences"][0] and not flipped["conclusions_stable"]


def test_every_case_has_frozen_answer_and_known_bottleneck_label():
    spec = load_cases([])
    assert 6 <= len(spec["cases"]) <= 9
    assert sum(c["bottleneck"]["model"] is None for c in spec["cases"]) == 1  # đúng một ca đối chứng
    for case in spec["cases"]:
        assert read_expected(case["id"]), case["id"]
        assert case["bottleneck"]["model"] in (case["target"], None)


@pytest.mark.slow
def test_perf_eval_two_rounds_writes_reports(tmp_path: Path):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    command = [
        sys.executable,
        "eval/run_perf.py",
        "--only",
        "range_join",
        "control_clean",
        "--no-tpch",
        "--repeat",
        "2",
    ]
    done = subprocess.run(  # noqa: S603 — lệnh cố định
        [*command, "--out", str(tmp_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    folders = list(tmp_path.glob("perf-*-mock"))
    assert len(folders) == 1, (done.stdout + done.stderr)[-2000:]
    out = folders[0]
    assert {p.name for p in out.iterdir()} == {"summary.md", "cases.csv", "details.json"}
    details = json.loads((out / "details.json").read_text(encoding="utf-8"))
    summary = details["summary"]
    assert len(details["rounds"]) == 2 and summary["stability"]["checked"] is True
    assert summary["provider"] == "mock" and summary["correct"] == "2/2" and summary["bottleneck_in_top_n"] == "1/1"
    rows = {r["id"]: r for r in csv.DictReader((out / "cases.csv").open(encoding="utf-8"))}
    assert rows["range_join"]["bottleneck_hit"] == "đạt" and rows["control_clean"]["decision"] == "skipped"
    assert rows["range_join"]["dag_wall_ms"] == "chưa đo" and rows["range_join"]["before_ms"] != "chưa đo"
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert "không đánh giá năng lực LLM" in text
    stable = summary["stability"]["stable"]
    assert ("kết quả chưa ổn định" in text) == (stable is False)
    assert done.returncode == (0 if summary["accepted"] else 1)
