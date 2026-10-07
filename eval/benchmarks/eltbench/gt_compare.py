"""So kết quả của pipeline với bảng kết quả đúng (CSV xuất từ Snowflake) — code tất định, không dùng LLM.

Bảng đúng có tên cột viết HOA, số làm tròn 6 chữ số, số nguyên dạng "1.0", thời gian dạng "2021-04-01 19:42:58.123"
(có khi giờ một chữ số "0:00:00", có khi kèm múi giờ "+0000"); ô kiểu VARIANT xuất dạng JSON (chuỗi có nháy kép
'"regular"', giá trị rỗng là chữ 'null'). Vì vậy: so tên cột không phân biệt hoa/thường, không phụ thuộc thứ tự cột;
so số lẻ với sai số, số nguyên so bằng; thời gian và VARIANT đưa về một dạng chung (UTC, mili giây) ở CẢ HAI bên;
so tập dòng hai chiều, không phụ thuộc thứ tự dòng.
"""

import json
import math
import re
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb

REL_TOL = 1e-5
ABS_TOL = 1e-6
BOOLEANS = {"true": 1.0, "false": 0.0}
SAMPLE_ROWS = 3  # số dòng mẫu in ra khi lệch
CELL_WIDTH = 40  # cắt ô dài khi in mẫu

# "2021-04-01 19:42:58.123", "2019-09-11 0:00:00", "2023-05-25T09:00:00.000 +0000", "...+00:00", "...+07", "...Z"
_TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?\s*(Z|[+-]\d{2}(?::?\d{2})?)?$")


def _canonical_time(day: str, hour: int, minute: int, second: int, fraction: str, offset: str | None) -> str:
    """Một dạng chung cho mọi thời điểm: UTC, giờ 2 chữ số, phần lẻ cắt về mili giây, bỏ số 0 thừa."""
    micro = int((fraction or "0")[:6].ljust(6, "0"))
    moment = datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}:{second:02d}").replace(microsecond=micro)
    if offset:
        digits = "0000" if offset == "Z" else offset[1:].replace(":", "").ljust(4, "0")
        offset = f"{'-' if offset[0] == '-' else '+'}{digits[:2]}:{digits[2:]}"
        moment = datetime.fromisoformat(f"{moment.isoformat()}{offset}").astimezone(UTC).replace(tzinfo=None)
    return _render(moment)


def _render(moment: datetime) -> str:
    text = moment.strftime("%Y-%m-%d %H:%M:%S")
    millis = f"{moment.microsecond // 1000:03d}".rstrip("0")
    return f"{text}.{millis}" if millis else text


def normalize(value: object) -> object:
    """Đưa một ô về dạng so được: None, số thực, hoặc chuỗi (thời gian ở dạng chung)."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float | Decimal):
        return float(value)
    if isinstance(value, datetime):
        moment = value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value
        return _render(moment)
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if text == "null":  # VARIANT rỗng
        return None
    if len(text) >= 2 and text[0] == text[-1] == '"':  # chuỗi VARIANT dạng JSON: "regular" → regular
        try:
            inner = json.loads(text)
        except ValueError:
            inner = None
        if isinstance(inner, str):
            return normalize(inner)
    if text.lower() in BOOLEANS:
        return BOOLEANS[text.lower()]
    if match := _TIMESTAMP.match(text):
        day, hour, minute, second, fraction, offset = match.groups()
        try:
            return _canonical_time(day, int(hour), int(minute), int(second), fraction, offset)
        except ValueError:
            return text
    try:
        return float(text)
    except ValueError:
        return text


def _sort_key(row: tuple) -> tuple:
    return tuple((0, "") if v is None else (1, f"{v:.3f}") if isinstance(v, float) else (2, v) for v in row)


def _same_cell(a: object, b: object) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        if a.is_integer() and b.is_integer():  # số nguyên (mã ID lớn, số đếm): so bằng, sai số tương đối làm lọt ID±1
            return a == b
        return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL) or (math.isnan(a) and math.isnan(b))
    return a == b


def _same_column(ours: list, truth: list) -> bool:
    """Cột khớp khi tập giá trị (kể cả lặp) khớp, không phụ thuộc thứ tự dòng."""
    key = _sort_key
    return all(map(_same_cell, sorted(ours, key=lambda v: key((v,))), sorted(truth, key=lambda v: key((v,)))))


def _short(value: object) -> str:
    text = "NULL" if value is None else str(value)
    return text if len(text) <= CELL_WIDTH else text[: CELL_WIDTH - 1] + "…"


def describe_mismatch(names: list[str], ours: list[tuple], truth: list[tuple]) -> str:
    """Tên cột lệch + tối đa 3 dòng mẫu (đúng / của agent), chỉ in các cột lệch."""
    bad = [i for i, _ in enumerate(names) if not _same_column([r[i] for r in ours], [r[i] for r in truth])]
    if not bad:  # mỗi cột riêng lẻ khớp, nhưng ghép thành dòng thì lệch
        bad = list(range(len(names)))
    pairs = [(a, b) for a, b in zip(ours, truth, strict=True) if not all(map(_same_cell, a, b))]
    samples = [
        "đúng=(" + ", ".join(_short(b[i]) for i in bad) + ") / agent=(" + ", ".join(_short(a[i]) for i in bad) + ")"
        for a, b in pairs[:SAMPLE_ROWS]
    ]
    return f"cột lệch {[names[i] for i in bad]}; mẫu: " + "; ".join(samples)


def load_ground_truth(csv_path: Path) -> tuple[list[str], list[tuple]]:
    """Đọc bảng đúng (mọi cột dạng chuỗi), tên cột chữ thường."""
    with duckdb.connect() as con:
        rel = con.sql(f"SELECT * FROM read_csv('{csv_path.as_posix()}', header = true, all_varchar = true)")
        return [c.lower() for c in rel.columns], rel.fetchall()


def compare_to_ground_truth(
    columns: list[str], rows: list[tuple], csv_path: Path, ignore_columns: frozenset[str] = frozenset()
) -> tuple[bool, str]:
    """So (cột, dòng) của pipeline với bảng đúng; trả (khớp?, mô tả).

    `ignore_columns`: cột đề yêu cầu nhưng bảng đúng không có (lỗi benchmark đã ghi trong known_issues.yaml) —
    bỏ khỏi đầu ra trước khi so. Mặc định rỗng: chấm nghiêm.
    """
    gt_columns, gt_rows = load_ground_truth(csv_path)
    lowered = [c.lower() for c in columns]
    keep = [i for i, c in enumerate(lowered) if c not in ignore_columns or c in gt_columns]
    lowered, rows = [lowered[i] for i in keep], [tuple(r[i] for i in keep) for r in rows]
    if sorted(lowered) != sorted(gt_columns):
        missing, extra = sorted(set(gt_columns) - set(lowered)), sorted(set(lowered) - set(gt_columns))
        duplicated = sorted(c for c, n in Counter(lowered).items() if n > 1)
        return False, f"Khác cột — thiếu {missing}, thừa {extra}" + (f", trùng {duplicated}" if duplicated else "")
    if len(rows) != len(gt_rows):
        return False, f"Khác số dòng: {len(rows)} ≠ {len(gt_rows)} (đúng)"
    order = [lowered.index(c) for c in gt_columns]
    ours = sorted((tuple(normalize(r[i]) for i in order) for r in rows), key=_sort_key)
    truth = sorted((tuple(normalize(v) for v in r) for r in gt_rows), key=_sort_key)
    wrong = sum(1 for a, b in zip(ours, truth, strict=True) if not all(map(_same_cell, a, b)))
    if wrong == 0:
        return True, f"Khớp {len(rows)} dòng"
    return False, f"{wrong}/{len(rows)} dòng khác bảng đúng — " + describe_mismatch(gt_columns, ours, truth)
