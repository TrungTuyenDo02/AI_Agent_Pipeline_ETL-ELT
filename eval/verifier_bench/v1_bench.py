"""V1 như một máy dò: chạy bộ ca tấn công (phải chặn) và ca hợp lệ (phải qua) qua đúng hàm kiểm tra của hệ thống.

Không gọi LLM. Dùng chung cho `run_bench.py` (báo cáo) và `tests/test_verifiers/test_v1_redteam.py` (CI: 0 ca lọt).
"""

import sys
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from src.agents.nodes.safety import check_dag, check_sql  # noqa: E402
from src.agents.tools.dbt_tools import is_allowed_path  # noqa: E402

# Danh mục thật giả định cho mọi ca SQL
V1_CATALOG = {
    "raw": {
        "orders": {
            "order_id": "VARCHAR",
            "customer_id": "VARCHAR",
            "order_date": "VARCHAR",
            "status": "VARCHAR",
            "amount": "BIGINT",
        },
        "customers": {"customer_id": "VARCHAR", "email": "VARCHAR", "city": "VARCHAR"},
    },
    "main": {
        "stg_orders": {
            "order_id": "VARCHAR",
            "customer_id": "VARCHAR",
            "order_date": "DATE",
            "status": "VARCHAR",
            "amount": "BIGINT",
        }
    },
}


class V1Case(BaseModel):
    """Một ca V1."""

    id: str
    kind: str  # sql | path | dag
    label: str  # block | pass
    labeled_by: str = "author"
    sql: str = ""
    path: str = ""
    note: str = ""
    found_leak: str | date = ""
    known_leak: bool = False  # lọt đã biết, rủi ro chặn ở lớp khác (ghi trong note)


class V1Result(BaseModel):
    """Kết quả một ca."""

    case: V1Case
    blocked: bool
    detail: str

    @property
    def correct(self) -> bool:
        """Đúng kỳ vọng: ca `block` bị chặn, ca `pass` được qua."""
        return self.blocked == (self.case.label == "block")


def load_cases(name: str) -> list[V1Case]:
    """Đọc v1_redteam.yaml / v1_valid.yaml."""
    data = yaml.safe_load((HERE / name).read_text(encoding="utf-8"))
    return [V1Case.model_validate(c) for c in data["cases"]]


def run_case(case: V1Case) -> V1Result:
    """Chạy đúng hàm của V1; mọi ngoại lệ chưa bắt được ghi rõ (lỗi của V1, dù vẫn tính là "chặn")."""
    try:
        if case.kind == "path":
            issues = [] if is_allowed_path(case.path) else [f"Đường dẫn không được phép: {case.path}"]
        elif case.kind == "dag":
            issues = check_dag(case.sql)
        else:
            issues = check_sql(case.sql, {k: dict(v) for k, v in V1_CATALOG.items()})[0]
    except Exception as exc:  # noqa: BLE001 — ghi nhận V1 vỡ thay vì báo lỗi gọn
        return V1Result(case=case, blocked=True, detail=f"V1 NÉM NGOẠI LỆ {type(exc).__name__}: {exc}"[:200])
    return V1Result(case=case, blocked=bool(issues), detail=(issues[0] if issues else "cho qua")[:200])


def run_all() -> list[V1Result]:
    """Mọi ca tấn công rồi mọi ca hợp lệ."""
    return [run_case(c) for c in load_cases("v1_redteam.yaml") + load_cases("v1_valid.yaml")]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for r in run_all():
        mark = "✓" if r.correct else "✗"
        print(f"{mark} [{r.case.label}] {r.case.id}: {r.detail}")
