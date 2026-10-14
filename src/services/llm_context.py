"""CỬA DUY NHẤT tạo ngữ cảnh dữ liệu đưa vào prompt (CLAUDE.md bản 2, mục 0.5 và 3.3).

`build_llm_context(user, source_ids, tables)` quyết định LLM được thấy gì theo mức `llm_access` của từng nguồn:

| Mức | LLM thấy | Không thấy |
|---|---|---|
| `schema_only` | tên bảng, tên cột, kiểu | mọi thống kê, mọi giá trị |
| `profile` (mặc định) | + số dòng, % rỗng, số giá trị khác nhau, tỷ lệ trùng khóa, dạng giá trị và phân bố | giá trị thật |
| `masked_sample` | + tối đa LLM_SAMPLE_MAX_ROWS dòng đã che | dòng chưa che |

Ràng buộc theo độ nhạy cảm (kiểm lần hai ở đây dù API đăng ký đã kiểm): `high` → `schema_only`; `medium` → tối đa `profile`;
`low` → tối đa `masked_sample`. Vượt mức thì HẠ xuống mức cho phép và ghi AuditLog. Thiếu thông tin mức/độ nhạy cảm của một bảng
(danh mục không đến từ sổ nguồn) → coi là `schema_only`. Không node nào được tự dựng ngữ cảnh dữ liệu bằng đường khác:
`tests/test_llm_context.py` quét mã nguồn và quét mọi prompt của một lần chạy thử để bảo đảm điều này.
"""

import logging
import time

from pydantic import BaseModel, Field

from src.agents.nodes.profiler import DATE_NAME_RE, MONEY_NAME_RE
from src.config import get_settings
from src.models.sources import DataSource, LLMAccess, UserContext, cap_access
from src.services import secrets, source_registry
from src.services.connectors import ConnectorError, SourceConnector, get_connector
from src.services.profiling import cached_table_profile, masked_sample
from src.services.prompt_context import compact_catalog, compact_profile, referenced_schema

logger = logging.getLogger(__name__)
PROFILE_TTL_SEC = 300  # hồ sơ của bảng CSDL ngoài nhớ chừng này giây (file thì nhớ tới khi file đổi)
_PROFILES: dict[tuple, tuple[float, dict]] = {}
MAX_FORMAT_COLUMNS = 8
MAX_NULL_COLUMNS = 6
SHOWN_SHAPES = 4
MIN_NULL_PCT = 1.0


class ContextTable(BaseModel):
    """Một bảng trong ngữ cảnh LLM. KHÔNG có đường dẫn file hay chuỗi kết nối."""

    name: str
    fmt: str = ""  # loại file/bảng (csv, json, parquet, sqlite)
    table: str = ""  # tên bảng trong file SQLite
    columns: dict[str, str]
    access: LLMAccess = "schema_only"
    profile: dict = Field(default_factory=dict)  # chỉ có ở mức profile trở lên
    sample: list[dict] = Field(default_factory=list)  # chỉ có ở mức masked_sample (đã che)


class LLMContext(BaseModel):
    """Ngữ cảnh dữ liệu cho prompt + danh mục cho code. Chỉ các phương thức `*_for_llm`/`planner_catalog`/`build_profile` đi vào prompt."""

    tables: list[ContextTable]
    catalog: list[dict] = Field(
        default_factory=list
    )  # CHO CODE (có path, mức truy cập): lưu vào state, không đưa vào prompt
    downgraded: list[str] = Field(default_factory=list)  # tên bảng đã bị hạ mức

    def level_of(self, table: str) -> LLMAccess:
        """Mức truy cập của một bảng; bảng lạ → schema_only."""
        found = next((t for t in self.tables if t.name == table), None)
        return found.access if found else "schema_only"

    def planner_catalog(self) -> list[dict]:
        """Danh mục cho Planner: tên, loại, cột → kiểu; từ mức `profile` thêm `stats` (số liệu do code đếm, không có giá trị)."""
        out = []
        for t in self.tables:
            entry = {"name": t.name, "kind": t.fmt, "columns": t.columns}
            if t.table:
                entry["table"] = t.table
            if t.profile:
                entry["stats"] = _planner_stats(t.profile)
            out.append(entry)
        return compact_catalog(out)

    def build_profile(self, profile: dict) -> dict:
        """Hồ sơ dữ liệu cho Codegen/Testgen từ kết quả bước P, cắt theo mức của từng bảng.

        schema_only: chỉ tên cột và kiểu. profile: số liệu + dạng định dạng đã phát hiện (không giá trị, không ví dụ). masked_sample:
        thêm dòng đã che. Bảng không có trong ngữ cảnh → schema_only.
        """
        out: dict = {}
        by_name = {t.name: t for t in self.tables}
        for table, info in profile.items():
            ctx = by_name.get(table)
            level = ctx.access if ctx else "schema_only"
            if level == "schema_only":
                out[table] = {"columns": {c: {"type": v.get("type")} for c, v in info.get("columns", {}).items()}}
                continue
            out[table] = compact_profile({table: info})[table]
            if level == "masked_sample" and ctx and ctx.sample:
                out[table]["sample"] = ctx.sample
        return out


def schema_for_sql(sql: str, catalog: dict[str, dict[str, dict[str, str]]]) -> dict:
    """Cấu trúc (tên bảng, cột, kiểu) của các bảng câu SQL đọc tới, cho Optimizer: luôn ở mức schema_only."""
    return referenced_schema(sql, catalog)


def _planner_stats(profile: dict) -> dict:
    stats = {
        k: profile[k]
        for k in ("rows", "few_values", "key_column", "repeated_keys", "repeated_keys_differing")
        if k in profile
    }
    columns = profile.get("columns", {})
    formats = {
        c: dict(list(info["shapes"].items())[:SHOWN_SHAPES])
        for c, info in columns.items()
        if info.get("shapes") and (len(info["shapes"]) > 1 or DATE_NAME_RE.search(c) or MONEY_NAME_RE.search(c))
    }
    if formats:
        stats["formats"] = dict(list(formats.items())[:MAX_FORMAT_COLUMNS])  # dạng giá trị: chữ số → 9, chữ cái → a
    nulls = {c: info["null_pct"] for c, info in columns.items() if info.get("null_pct", 0) >= MIN_NULL_PCT}
    if nulls:
        stats["null_pct"] = dict(sorted(nulls.items(), key=lambda kv: -kv[1])[:MAX_NULL_COLUMNS])
    return stats


def _profile(item: dict, connector: SourceConnector | None, restricted: tuple[str, ...]) -> dict:
    """Hồ sơ thống kê của một bảng: qua bộ nạp của nguồn (tệp: nhớ tới khi file đổi; CSDL ngoài: nhớ vài phút). Bộ nạp lỗi
    (mất kết nối, thiếu bí mật) → bảng đó tạm chỉ có cấu trúc, các bảng khác vẫn đủ."""
    if connector is None:
        return cached_table_profile(item, item.get("sensitivity", "medium"), list(restricted))
    key = (item.get("source_id"), item["name"], tuple(sorted(item.get("columns", {}))))
    if (
        item.get("source_kind") != "file"
        and (hit := _PROFILES.get(key))
        and time.monotonic() - hit[0] < PROFILE_TTL_SEC
    ):
        return hit[1]
    try:
        profile = connector.get_profile(item["name"]).model_dump()
    except (ConnectorError, secrets.SecretError) as exc:
        logger.warning("profile unavailable", extra={"table": item["name"], "reason": str(exc)[:200]})
        return {}
    _PROFILES[key] = (time.monotonic(), profile)
    return profile


def _sample(item: dict, connector: SourceConnector | None, restricted: tuple[str, ...], rows: int) -> list[dict]:
    """Dòng mẫu đã che: qua bộ nạp của nguồn (`sample()` tự từ chối nếu mức không phải masked_sample)."""
    if connector is None:
        return masked_sample(item, rows, restricted)
    try:
        return connector.sample(item["name"], rows)
    except (ConnectorError, secrets.SecretError) as exc:
        logger.warning("sample unavailable", extra={"table": item["name"], "reason": str(exc)[:200]})
        return []


def _level_of(item: dict, downgraded: list[str]) -> LLMAccess:
    declared = item.get("llm_access") or "schema_only"
    sensitivity = item.get("sensitivity") or "high"
    allowed = cap_access(sensitivity, declared)
    if allowed != declared:
        downgraded.append(item["name"])
    return allowed


def build_llm_context(
    user: UserContext | str,
    source_ids: list[int] | None = None,
    tables: list[str] | None = None,
    *,
    catalog: list[dict] | None = None,
    run_id: str = "",
    audit: bool = False,
) -> LLMContext:
    """Dựng ngữ cảnh dữ liệu cho prompt của `user`.

    `catalog`: danh mục đã lấy từ `source_registry.visible_catalog` (tránh hỏi lại sổ nguồn); không có thì tự lấy. Chỉ bảng `user`
    được thấy mới vào ngữ cảnh. `audit=True`: ghi AuditLog (`llm.context`) ai, nguồn nào, mức nào, lần chạy nào.
    """
    resolved: list[UserContext] = []

    def who() -> UserContext:  # chỉ hỏi sổ người dùng khi thật sự cần (lấy danh mục, ghi AuditLog)
        if not resolved:
            resolved.append(user if isinstance(user, UserContext) else source_registry.user_context(user))
        return resolved[0]

    items = catalog if catalog is not None else source_registry.visible_catalog(who(), source_ids)
    if tables is not None:
        wanted = set(tables)
        items = [i for i in items if i["name"] in wanted]
    settings = get_settings()
    sources: dict[int, DataSource] = {}

    def connector_for(item: dict) -> SourceConnector | None:
        """Bộ nạp của nguồn chứa bảng này (qua sổ nguồn, một lần hỏi cho cả lượt); danh mục không có `source_id` thì None."""
        if item.get("source_id") is None:
            return None
        if not sources:
            sources.update({s.id: s for s in source_registry.list_sources()})
        source = sources.get(item["source_id"])
        return get_connector(source) if source else None

    downgraded: list[str] = []
    out: list[ContextTable] = []
    code_items: list[dict] = []
    for item in items:
        level = _level_of(item, downgraded)
        restricted = tuple(item.get("restricted_columns") or ())
        connector = connector_for(item) if level != "schema_only" else None
        profile = _profile(item, connector, restricted) if level != "schema_only" else {}
        sample = _sample(item, connector, restricted, settings.llm_sample_max_rows) if level == "masked_sample" else []
        out.append(
            ContextTable(
                name=item["name"],
                fmt=item.get("kind", ""),
                table=item.get("table", ""),
                columns=dict(item.get("columns", {})),
                access=level,
                profile=profile,
                sample=sample,
            )
        )
        code_items.append({**{k: v for k, v in item.items() if k != "sample"}, "llm_access": level})
    if downgraded:
        logger.warning("llm access downgraded", extra={"tables": downgraded})
        source_registry.audit_access(who(), "llm_access.downgraded", _source_ids(items), run_id, tables=downgraded)
    if audit and items:
        levels = sorted({t.access for t in out})
        source_registry.audit_access(who(), "llm.context", _source_ids(items), run_id, levels=levels, tables=len(out))
    return LLMContext(tables=out, catalog=code_items, downgraded=downgraded)


def context_for_state(state: dict, tables: list[str] | None = None, *, audit: bool = False) -> LLMContext:
    """Ngữ cảnh cho một node của graph: danh mục trong state (đã lọc quyền khi Planner chạy) hoặc, nếu chưa có, danh mục mà người
    tạo lần chạy được thấy trong sổ nguồn."""
    return build_llm_context(
        state.get("requester", ""),
        catalog=state.get("source_catalog") or None,
        tables=tables,
        run_id=state.get("run_id", ""),
        audit=audit,
    )


def _source_ids(items: list[dict]) -> list[int]:
    return sorted({i["source_id"] for i in items if i.get("source_id") is not None})
