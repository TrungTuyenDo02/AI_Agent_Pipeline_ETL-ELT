"""Rút gọn ngữ cảnh gửi LLM (chuẩn prompt U1, quy tắc 2.2-9): chỉ trường node cần, JSON gọn, bỏ giá trị rỗng.

Chỉ dùng khi dựng prompt; state, giao diện và bằng chứng vẫn giữ bản đầy đủ.
"""

import sqlglot
from sqlglot import exp

# Trường spec mà Codegen/Testgen không dùng: mode_reason, signals (code tự tính), unknowns/questions (V0 đã bắt
# rỗng), plan_summary và lý do từng bước (viết cho người duyệt).
BUILD_SPEC_KEYS = ("request_text", "mode", "target", "grain", "output_columns", "metrics", "filters", "assumptions")


def _drop_empty(value: dict) -> dict:
    return {k: v for k, v in value.items() if v not in ("", [], {}, None)}


def spec_for_build(spec: dict) -> dict:
    """Spec cho Codegen/Testgen: tên nguồn (không đường dẫn), cột, chỉ số, bộ lọc, giả định, các bước kế hoạch."""
    out = {k: spec[k] for k in BUILD_SPEC_KEYS if spec.get(k) not in (None, "", [], {})}
    out["sources"] = [s["name"] for s in spec.get("sources", [])]
    out["output_columns"] = [_drop_empty(c) for c in spec.get("output_columns", [])]
    options = spec.get("options") or {}
    out["options"] = _drop_empty(
        {k: options.get(k) for k in ("load_mode", "incremental_column", "schedule")}
    )  # chỉ lựa chọn: lý do (có số dòng) và kết nối không gửi LLM
    if spec.get("decisions"):
        out["decisions"] = spec["decisions"]
    if spec.get("plan"):
        out["plan"] = [_drop_empty({"title": s.get("title"), "detail": s.get("detail")}) for s in spec["plan"]]
    return out


# Không gửi LLM: `examples` (giá trị thật, CLAUDE.md 2.3: LLM chỉ thấy cấu trúc), `nulls` (đã có null_pct),
# `categories` (chỉ để so cấu trúc), `date_order`/`uncertain` (cho người duyệt).
NOT_FOR_LLM = ("examples", "nulls", "categories", "date_order", "uncertain")


def _column(info: dict) -> dict:
    """Bỏ các khóa NOT_FOR_LLM, danh sách rỗng và `parse_failures` = 0 (mục 9: LLM không được lấy giá trị từ dữ liệu
    làm giá trị hợp lệ)."""
    out = {k: v for k, v in info.items() if k not in NOT_FOR_LLM and v not in ([], "", None)}
    if out.get("parse_failures") == 0:
        out.pop("parse_failures")
    return out


def compact_profile(profile: dict) -> dict:
    """Hồ sơ dữ liệu gọn: mỗi bảng số dòng, khóa, số khóa trùng, cột (kiểu, % rỗng, định dạng, biểu thức đọc đúng)."""
    out = {}
    for table, info in profile.items():
        item = {"rows": info.get("rows"), "columns": {c: _column(v) for c, v in info.get("columns", {}).items()}}
        if info.get("key_column"):
            item.update(key_column=info["key_column"], duplicate_keys=info.get("duplicate_keys", 0))
        out[table] = item
    return out


def compact_catalog(catalog: list[dict]) -> list[dict]:
    """Danh mục nguồn cho Planner: tên, loại, cột → kiểu, số liệu do code đếm (`stats`, không có giá trị dữ liệu).

    Không gửi dòng mẫu (CLAUDE.md 2.3) và đường dẫn file (code tự điền `kind`/`path` sau khi Planner chọn nguồn).
    """
    out = []
    for item in catalog:
        columns = item.get("columns", {})
        entry = {"name": item["name"], "kind": item.get("kind", ""), "columns": columns}
        if item.get("table"):
            entry["table"] = item["table"]
        if item.get("stats"):
            entry["stats"] = item["stats"]
        out.append(entry)
    return out


def referenced_schema(sql: str, catalog: dict[str, dict[str, dict[str, str]]]) -> dict:
    """Chỉ schema của các bảng câu SQL đọc tới (bảng không tìm thấy thì bỏ qua)."""
    try:
        tables = {(t.db or "main", t.name) for t in sqlglot.parse_one(sql, read="duckdb").find_all(exp.Table)}
    except sqlglot.errors.ParseError:
        return catalog
    out: dict[str, dict] = {}
    for schema, name in sorted(tables):
        if name in catalog.get(schema, {}):
            out.setdefault(schema, {})[name] = catalog[schema][name]
    return out or catalog
