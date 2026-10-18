"""Cổng duyệt J2 (V, code thuần, 0 token): 4 kiểm tra bắt buộc tính từ state, dùng chung cho bằng chứng, API và CLI.

State thiếu bằng chứng (checkpoint cũ, chưa chạy tới bước đó) → "chưa kiểm chứng", không bao giờ tự coi là đạt.
"""

from src.agents.state import PipelineState
from src.models.evidence import GateCheck, ReviewGate

UNVERIFIED_V2 = "Chưa có kết quả dbt build trên sandbox (V2)."


def _check(id_: str, name: str, status: str, reason: str) -> GateCheck:
    return GateCheck(id=id_, name=name, status=status, reason=reason)


def _model_run(sandbox: dict) -> GateCheck:
    name = "Model dbt chạy được trên sandbox"
    if not sandbox or "models_total" not in sandbox:
        return _check("model_run", name, "unverified", UNVERIFIED_V2)
    ok, total = sandbox.get("models_ok", 0), sandbox["models_total"]
    passed = bool(sandbox.get("passed")) and 0 < ok == total
    reason = f"{ok}/{total} model chạy được" + ("" if sandbox.get("passed") else "; dbt build không đạt")
    return _check("model_run", name, "passed" if passed else "failed", reason)


def _dag(safety: dict, files: dict) -> GateCheck:
    name = "DAG nạp được, phụ thuộc đúng, cấu hình hợp lệ, đích sandbox"
    if not safety:
        return _check("dag", name, "unverified", "Chưa có kết quả kiểm tra an toàn (V1).")
    if not any(p.startswith("dags/") for p in files):
        return _check("dag", name, "failed", "Thiếu DAG Airflow trong thư mục dags/.")
    if not safety.get("passed"):
        issues = [i for i in safety.get("issues", []) if i.startswith("dags/")] or safety.get("issues", [])
        return _check("dag", name, "failed", "; ".join(issues[:2]) or "V1 không đạt.")
    return _check("dag", name, "passed", "Kiểm AST (V1): cú pháp, thứ tự, vòng lặp, task mồ côi, lịch, retries, đích.")


def _dbt_tests(sandbox: dict) -> GateCheck:
    name = "dbt tests đạt"
    if not sandbox or "tests_total" not in sandbox:
        return _check("dbt_tests", name, "unverified", UNVERIFIED_V2)
    ok, total = sandbox.get("tests_ok", 0), sandbox["tests_total"]
    if total == 0:
        return _check("dbt_tests", name, "failed", "Không có dbt test nào chạy.")
    passed = bool(sandbox.get("passed")) and ok == total
    return _check("dbt_tests", name, "passed" if passed else "failed", f"{ok}/{total} test đạt")


def _expected(state: PipelineState, sandbox: dict) -> GateCheck:
    name = "Kết quả khớp kỳ vọng"
    if not sandbox or "test_files" not in state:
        return _check("expected", name, "unverified", "Thiếu test độc lập của Testgen hoặc kết quả V2.")
    tests = [p for p in state["test_files"] if p.startswith("tests/") and p.endswith(".sql")]
    if not tests:
        return _check("expected", name, "failed", "Không có test độc lập (Testgen) so kết quả với đặc tả.")
    if not sandbox.get("passed"):
        return _check("expected", name, "failed", "Test kỳ vọng hoặc kiểu cột theo đặc tả không đạt (V2).")
    reason = f"{len(tests)} test độc lập của Testgen (gồm đối soát) đạt; kiểu cột bảng đích khớp đặc tả."
    return _check("expected", name, "passed", reason)


def _optimization(state: PipelineState) -> GateCheck:
    name = "Bản tối ưu giống hệt bản gốc trên sandbox"
    report = state.get("optimization") or {}
    if report.get("decision") != "applied":
        return _check("optimization", name, "passed", "Không áp dụng bản tối ưu: giữ nguyên bản gốc.")
    sandbox = [c for c in report.get("equivalence", []) if c.get("dataset") == "sandbox"]
    if not sandbox:
        return _check("optimization", name, "unverified", "Chưa có đối chiếu với bản gốc trên dữ liệu sandbox.")
    return _check(
        "optimization", name, "passed" if sandbox[-1].get("equal") else "failed", sandbox[-1].get("detail", "")
    )


def review_gate(state: PipelineState) -> ReviewGate:
    """4 kiểm tra bắt buộc (chặn duyệt) + kiểm tra bổ sung (không chặn)."""
    sandbox, safety = state.get("sandbox") or {}, state.get("safety") or {}
    checks = [
        _model_run(sandbox),
        _dag(safety, state.get("code_files") or {}),
        _dbt_tests(sandbox),
        _expected(state, sandbox),
    ]
    airflow = _check(
        "airflow_run",
        "Airflow chạy thật trên sandbox, chạy lại không nhân đôi dữ liệu",
        "unverified",
        "Môi trường không có Airflow; DAG chỉ được kiểm bằng AST.",
    )
    return ReviewGate(
        passed=all(c.status == "passed" for c in checks), checks=checks, extra=[airflow, _optimization(state)]
    )


def gate_problems(state: PipelineState) -> list[str]:
    """Lý do chưa được duyệt (rỗng = được duyệt)."""
    return [f"{c.name}: {c.reason}" for c in review_gate(state).checks if c.status != "passed"]
