"""Tạo vài thay đổi cấu trúc nguồn GIẢ trong dữ liệu demo để xem trang "Thay đổi cấu trúc" và nút đỏ ở chuông.

    python demo/seed_drift.py          # chạy khi demo đã khởi động (dùng cùng cơ sở dữ liệu SQLite của demo)

Cách làm: chụp cấu trúc thật của nguồn "P113 Retail" làm bản chuẩn, rồi giả lập backend đổi cấu trúc (đổi tên cột, đổi kiểu, xóa cột,
thêm cột) và chạy đúng bộ phát hiện của hệ thống. Không sửa file nguồn, không tạo run, không gọi LLM. Chạy lại nhiều lần vẫn an toàn.
"""

import copy
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.run_demo import demo_env  # noqa: E402

os.environ.update(demo_env())

from src.services import schema_drift as drift  # noqa: E402
from src.services import source_registry as registry  # noqa: E402
from src.services.connectors import get_connector  # noqa: E402


def rename(columns: dict, old: str, new: str) -> dict:
    return {(new if name == old else name): meta for name, meta in columns.items()}


def drifted(tables: dict) -> dict:
    out = copy.deepcopy(tables)
    out["shopee_orders"] = rename(out["shopee_orders"], "order_date", "ordered_at")  # đổi tên cột
    out["payments"]["amount"]["type"] = "string"  # decimal/float → chuỗi: không tương thích
    out["tiki_orders"].pop("buyer_email")  # xóa cột
    out["website_orders"]["coupon_code"] = {"type": "string", "nullable": True, "position": 99}  # thêm cột
    out["website_orders"]["amount_vnd"]["type"] = "float"  # integer → float: mở rộng an toàn
    return out


def main() -> int:
    source = registry.list_sources()[0]
    real = drift.current_tables(get_connector(source))
    drift.capture_snapshot(source, real)  # bản chuẩn (phiên bản 1)
    drift.current_tables = lambda _connector: drifted(real)  # giả lập backend đã đổi
    created, _ = drift.check_source(source)
    print(f"Nguồn: {source.name} — ghi {len(created)} thay đổi mới.")
    for change in drift.list_changes([source.id], status="open"):
        print(f"  [{change.severity:<8}] {change.table}: {change.change_type} — {change.detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
