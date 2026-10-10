"""Kiểm liên kết tương đối trong mọi file .md của repo (không có link chết, ảnh có thật).

    python scripts/check_md_links.py          # thoát mã 1 nếu có link chết

Bỏ qua: liên kết http(s)/mailto, neo `#...` trong cùng file, thư mục không phải mã nguồn (node_modules, .venv, ...),
và nội dung trong khối mã (```).
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"node_modules", ".venv", ".git", ".next", ".pytest_cache", ".ruff_cache", "__pycache__", ".ai-log", "data"}
SKIP_FILES = {"CLAUDE.md"}  # file riêng của người dùng, đã git-ignore
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def markdown_files() -> list[Path]:
    return sorted(
        p
        for p in ROOT.rglob("*.md")
        if not (set(p.relative_to(ROOT).parts) & SKIP_DIRS) and p.name not in SKIP_FILES
    )


def broken_links(path: Path) -> list[str]:
    errors = []
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK_RE.findall(re.sub(r"`[^`]*`", "", line)):
            if target.startswith(("http://", "https://", "mailto:", "#", "<")):
                continue
            file_part = unquote(target.split("#", 1)[0])
            if not file_part:
                continue
            resolved = (ROOT / file_part.lstrip("/")) if file_part.startswith("/") else (path.parent / file_part)
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}:{number}: link chết → {target}")
    return errors


def main() -> int:
    errors = [error for path in markdown_files() for error in broken_links(path)]
    for error in errors:
        print(error)
    print(f"Đã kiểm {len(markdown_files())} file .md: " + (f"{len(errors)} link chết." if errors else "không có link chết."))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
