"""Oracle Extract độc lập, phản chứng bộ chấm và chạy connector/registry thật trong tiến trình cô lập."""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

import run_eval  # noqa: E402
from extract_score import compare_snapshot, summarize  # noqa: E402

DATASET = ROOT / "eval" / "datasets" / "extract_v1"
MANIFEST = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
EXPECTED = json.loads((DATASET / "expected.json").read_text(encoding="utf-8"))


def run_bench(dataset: Path, output: Path) -> tuple[int, dict]:
    done = subprocess.run(
        [sys.executable, str(ROOT / "eval" / "run_extract.py"), "--dataset", str(dataset), "--output-dir", str(output)],
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    path = output / "extract.json"
    assert path.exists(), (done.stdout + done.stderr)[-2000:]
    return done.returncode, json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    code, report = run_bench(DATASET, tmp_path_factory.mktemp("extract-score"))
    assert code == 0, [r for r in report["cases"] if not r["passed"]]
    return report


@pytest.mark.parametrize("case_id", [c["id"] for c in MANIFEST["cases"]])
def test_extract_matches_frozen_oracle(measured, case_id):
    case = next(r for r in measured["cases"] if r["id"] == case_id)
    assert case["passed"] and all(case["checks"].values()), case
    assert case["expected_digest"] == case["actual_digest"]


def test_receipts_identify_same_named_sources_and_input_bytes(measured):
    cases = {r["id"]: r for r in measured["cases"]}
    sales, finance = cases["csv_exact"], cases["same_name_other_department"]
    assert sales["actual_rows"] == finance["actual_rows"] == 6
    assert sales["receipt"]["source_id"] != finance["receipt"]["source_id"]
    assert sales["actual_digest"] != finance["actual_digest"]
    for case in (sales, finance):
        receipt = case["receipt"]
        expected = hashlib.sha256((DATASET / "sources" / receipt["artifact"]).read_bytes()).hexdigest()
        assert receipt["input_sha256"] == expected
    assert measured["oracle_sha256"] == hashlib.sha256((DATASET / "expected.json").read_bytes()).hexdigest()


def test_all_security_and_provenance_gates_pass(measured):
    gates = [r for r in measured["cases"] if r["critical"]]
    assert len(gates) >= 8 and all(r["passed"] for r in gates)
    assert measured["summary"]["accepted"] and measured["llm_calls"] == 0
    assert "PostgreSQL thật" in measured["not_evaluated"]


@pytest.mark.parametrize("tamper", ["wrong_value", "wrong_department"])
def test_tampered_source_fails_with_unchanged_oracle(tmp_path: Path, tamper: str):
    dataset = tmp_path / "dataset"
    shutil.copytree(DATASET, dataset)
    original_oracle = (dataset / "expected.json").read_bytes()
    target = dataset / "sources" / "partner_sales" / "orders.csv"
    if tamper == "wrong_value":
        target.write_bytes(target.read_bytes().replace(b"125000", b"125099", 1))
    else:
        shutil.copyfile(dataset / "sources" / "partner_finance" / "orders.csv", target)
    code, report = run_bench(dataset, tmp_path / "result")
    assert code == 1 and report["summary"]["accepted"] is False
    failed = next(r for r in report["cases"] if r["id"] == "csv_exact")
    assert not failed["passed"] and failed["checks"]["row_count_exact"]
    assert not failed["checks"]["rows_exact_with_duplicates"]
    assert (dataset / "expected.json").read_bytes() == original_oracle


@pytest.mark.parametrize("mutation", ["value", "duplicate", "schema", "empty_schema"])
def test_scorer_rejects_wrong_outputs(mutation: str):
    expected = copy.deepcopy(EXPECTED["sales_orders"])
    observed = copy.deepcopy(expected)
    if mutation == "value":
        observed["rows"][0][3] = "99999999"
    elif mutation == "duplicate":
        observed["rows"][3] = list(observed["rows"][0])
    else:
        observed["schema"][0][0] = "wrong_id"
        if mutation == "empty_schema":
            expected["rows"] = observed["rows"] = []
    assert not compare_snapshot(expected, observed)["passed"]


def test_scorer_accepts_row_reordering_but_critical_failure_blocks_acceptance():
    expected = EXPECTED["sales_orders"]
    observed = {**expected, "rows": list(reversed(expected["rows"]))}
    assert compare_snapshot(expected, observed)["passed"]
    result = summarize([{"id": "good", "passed": True}, {"id": "leak", "passed": False, "critical": True}])
    assert result["pass_rate_pct"] == 50 and not result["accepted"]
    assert result["critical_failures"] == ["leak"]
    assert not summarize([])["accepted"]


def test_eval_step_propagates_nonzero_exit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        run_eval.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="failed", stderr="", returncode=3)
    )
    with pytest.raises(SystemExit) as error:
        run_eval.run_step([sys.executable, "deliberately-failing-step"])
    assert error.value.code == 3


def test_extract_metric_does_not_invent_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(run_eval, "load", lambda name: None)
    assert "chưa đo" in run_eval.extract_lines()[0]
    measured = {"dataset_id": "fixture", "summary": {"accepted": False, "passed": 2, "total": 3}}
    monkeypatch.setattr(run_eval, "load", lambda name: measured)
    line = run_eval.extract_lines()[0]
    assert "2/3" in line and "chưa đạt" in line and "chưa đo PostgreSQL thật" in line
