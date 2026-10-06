"""Chấm bảng đích DE làm tay bằng đúng bộ chấm của golden (so `expected.csv`), xem eval/baseline/PROTOCOL.md mục 5.

python eval/baseline/check_de.py g01_three_sources --db path/to/dev.duckdb --table fct_daily_revenue
"""

import argparse
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "benchmarks" / "eltbench"))

from gt_compare import compare_to_ground_truth  # noqa: E402

CASES_DIR = ROOT / "eval" / "datasets" / "golden"
TABLE_RE = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)?$")


def read_table(db: Path, table: str) -> tuple[list[str], list[tuple]]:
    """Cột và dòng của bảng (mở chỉ đọc). `table` dạng `ten_bang` hoặc `schema.ten_bang`."""
    if not TABLE_RE.match(table):
        raise ValueError(f"Tên bảng không hợp lệ: {table!r} (chỉ chữ, số, _ và một dấu chấm)")
    quoted = ".".join(f'"{part}"' for part in table.split("."))
    with duckdb.connect(str(db), read_only=True) as con:
        rel = con.sql(f"SELECT * FROM {quoted}")
        return rel.columns, rel.fetchall()


def check(case_id: str, db: Path, table: str) -> tuple[bool, str]:
    """(khớp?, mô tả) của bảng DE so với expected.csv của ca."""
    expected = CASES_DIR / case_id / "expected.csv"
    if not expected.exists():
        return False, f"Không có ca {case_id} (thiếu {expected.relative_to(ROOT)})"
    if not db.exists():
        return False, f"Không thấy file DuckDB: {db}"
    try:
        columns, rows = read_table(db, table)
    except (ValueError, duckdb.Error) as exc:
        return False, f"Không đọc được bảng: {str(exc).splitlines()[0]}"
    return compare_to_ground_truth(columns, rows, expected)


def main() -> None:
    """In kết quả chấm; mã thoát 1 nếu lệch."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("case_id", help="tên thư mục ca trong eval/datasets/golden")
    parser.add_argument("--db", type=Path, required=True, help="file DuckDB DE đã build")
    parser.add_argument("--table", required=True, help="bảng đích, ví dụ fct_daily_revenue hoặc main.fct_daily_revenue")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ok, detail = check(args.case_id, args.db, args.table)
    print(f"{'✓' if ok else '✗'} {args.case_id}: {detail}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
