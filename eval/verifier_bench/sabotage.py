"""Plugin pytest CỐ Ý LÀM HỎNG một bước V (biến môi trường P113_SABOTAGE) để kiểm bộ test của V có đỏ không.

Chỉ dùng cho `run_bench.py` (tự kiểm test của V). Không bao giờ nạp trong CI hay lúc chạy thật.

    P113_SABOTAGE=v1 pytest -p sabotage tests/test_verifiers/test_v1_redteam.py   (PYTHONPATH chứa eval/verifier_bench)
"""

import os

SABOTAGES = {
    "v0": "V0 Soát spec luôn đạt (bỏ kiểm điểm chưa rõ + trường bắt buộc)",
    "v1": "V1 An toàn không tìm lệnh/hàm nguy hiểm",
    "v2": "V2 Sandbox coi mọi lần dbt build là đạt",
    "v3": "V3 Đối chiếu luôn coi hai kết quả là giống",
}


def _apply(kind: str) -> None:
    if kind == "v0":
        from src.agents.nodes import spec_check

        spec_check._unknowns = lambda spec: []
        spec_check._required_fields = lambda spec: []
    elif kind == "v1":
        from src.agents.nodes import safety

        safety.find_unsafe_constructs = lambda tree: []
        safety.dangerous_dag_code = lambda tree: []
    elif kind == "v2":
        from src.agents.nodes import sandbox_run

        original = sandbox_run.run_dbt_build
        sandbox_run.run_dbt_build = lambda workspace: original(workspace).model_copy(update={"ok": True})
    elif kind == "v3":
        from src.agents.nodes import compare

        compare.compare_results = lambda a, b, abs_tol: (True, "bị phá (sabotage)")


def pytest_collection_finish(session) -> None:  # noqa: ARG001 — hook của pytest
    """Phá sau khi đã nạp xong module test (để thay đúng tên toàn cục mà hàm của V gọi tới)."""
    kind = os.environ.get("P113_SABOTAGE", "")
    if kind:
        _apply(kind)
