"""Kiểm bảng WORKLOG.md: mỗi dòng đúng 5 ô, không dòng trống chen giữa bảng, Status hợp lệ, Task/Output không quá dài.

python scripts/check_worklog.py            # kiểm WORKLOG.md; thoát mã 1 nếu có lỗi
"""

import re
import sys
from pathlib import Path

STATUSES = ("✅ Done", "🔄 Doing", "⚠️ Chưa sửa", "⏳ Chưa làm")
HEADER = "| Member | Task | Status | Output | Time |"
MAX_TASK_WORDS = 20
MAX_OUTPUT_WORDS = 25
TIME_RE = re.compile(r"^(—|~\d+(\.\d+)?\s?(h|giờ|phút|ngày))$")


def split_cells(line: str) -> list[str]:
    """Tách ô theo dấu gạch đứng, bỏ qua dấu có gạch ngược đứng trước."""
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def check(text: str) -> list[str]:
    """Danh sách lỗi (rỗng = đạt)."""
    errors: list[str] = []
    lines = text.split("\n")
    in_table = False
    for number, line in enumerate(lines, start=1):
        if line.startswith("|"):
            if line.strip() == HEADER:
                in_table = True
                continue
            if line.startswith("|--"):
                continue
            if not in_table:
                errors.append(f"dòng {number}: dòng bảng nằm ngoài bảng có tiêu đề chuẩn")
                continue
            cells = split_cells(line)
            if len(cells) != 5:
                errors.append(f"dòng {number}: có {len(cells)} ô, cần đúng 5 (ký tự `|` trong ô phải thay bằng `/`)")
                continue
            member, task, status, output, time = cells
            if status not in STATUSES:
                errors.append(f"dòng {number}: Status '{status}' không thuộc {', '.join(STATUSES)}")
            if len(task.split()) > MAX_TASK_WORDS:
                errors.append(f"dòng {number}: Task dài {len(task.split())} từ (tối đa {MAX_TASK_WORDS})")
            if len(output.split()) > MAX_OUTPUT_WORDS:
                errors.append(f"dòng {number}: Output dài {len(output.split())} từ (tối đa {MAX_OUTPUT_WORDS})")
            if not member or not task or not output:
                errors.append(f"dòng {number}: ô Member/Task/Output đang trống")
            if not TIME_RE.match(time):
                errors.append(f"dòng {number}: Time '{time}' phải là `—` hoặc dạng `~2h`")
        elif in_table and not line.strip():
            following = next((x for x in lines[number:] if x.strip()), "")
            if following.startswith("|") and not following.startswith("| Member"):
                errors.append(f"dòng {number}: dòng trống chen giữa bảng")
            in_table = False
        elif in_table:
            in_table = False
    return errors


def main() -> int:
    path = Path(__file__).resolve().parents[1] / "WORKLOG.md"
    errors = check(path.read_text(encoding="utf-8"))
    for error in errors:
        print(f"WORKLOG.md {error}")
    print("WORKLOG.md hợp lệ." if not errors else f"{len(errors)} lỗi.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
