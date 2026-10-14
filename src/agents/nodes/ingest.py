"""E0 Nhận nguồn (code): nạp các nguồn trong spec vào schema `raw` của sandbox DuckDB qua khung bộ nạp (`SourceConnector`).

Mỗi nguồn trong sổ nguồn có bộ nạp riêng (tệp, DuckDB, PostgreSQL chỉ đọc); bộ nạp chỉ lấy tập con có hạt giống cố định
(`SANDBOX_LOAD_MAX_ROWS`) và băm cột nhạy cảm của nguồn độ nhạy cảm cao. Dữ liệu này chỉ ở sandbox DuckDB của lần chạy, không về phía LLM.
"""

import logging

import duckdb

from src.agents.nodes.common import SANDBOX_DB, spec_of
from src.agents.state import PipelineState
from src.agents.tools.dbt_tools import prepare_workspace, write_sources_yml
from src.agents.tools.duckdb_tools import SourceInfo, load_sources
from src.agents.tools.scrub import scrub_error
from src.config import get_settings
from src.models.schemas import RunStatus
from src.services import secrets, source_registry
from src.services.connectors import ConnectorError, get_connector

logger = logging.getLogger(__name__)
NOT_VISIBLE = "Bạn không còn quyền dùng một trong các nguồn của lần chạy này (đã bị thu hồi hoặc nguồn đã tắt)."


def _load(items: list[dict], database: str, state: PipelineState) -> dict[str, int]:
    """Nạp từng nguồn qua bộ nạp của nó. Danh mục không đến từ sổ nguồn (không có `source_id`) đi đường tệp cũ."""
    max_rows = get_settings().sandbox_load_max_rows
    counts: dict[str, int] = {}
    by_source: dict[int, list[str]] = {}
    legacy: list[dict] = []
    for item in items:
        if item.get("source_id") is None:
            legacy.append(item)
        else:
            by_source.setdefault(item["source_id"], []).append(item["name"])
    with duckdb.connect(database) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        if by_source:
            user = source_registry.user_context(state.get("requester", ""))
            visible = {s.id: s for s in source_registry.get_visible_sources(user) if s.enabled}
            if not set(by_source) <= set(visible):  # quyền có thể đã đổi từ lúc lập kế hoạch (kiểm lại ở mọi đường vào)
                raise ConnectorError(NOT_VISIBLE)
            for source_id, names in by_source.items():
                counts |= get_connector(visible[source_id]).load_to_sandbox(names, con, max_rows)
        if legacy:
            counts |= load_sources(con, [SourceInfo.model_validate(i) for i in legacy], max_rows)
    return counts


def ingest_node(state: PipelineState) -> dict:
    """Tạo workspace, nạp nguồn dạng bảng; nguồn ảnh/PDF chỉ được ghi nhận (OCR là phần mở rộng)."""
    wanted = {s.name for s in spec_of(state).sources}
    items = [i for i in state.get("source_catalog", []) if i["name"] in wanted]
    workspace = prepare_workspace(state["run_id"])
    ids = sorted({i["source_id"] for i in items if i.get("source_id") is not None})
    source_registry.audit_access(
        state.get("requester", ""), "source.ingest", ids, state["run_id"], tables=sorted(wanted)
    )
    try:
        counts = _load(items, str(workspace / SANDBOX_DB), state)
    except (duckdb.Error, OSError, ConnectorError, secrets.SecretError) as exc:
        logger.error("ingest failed", extra={"error": type(exc).__name__})
        return {
            "status": RunStatus.FAILED.value,
            "error": f"Không nạp được nguồn dữ liệu: {scrub_error(str(exc))[:200]}",
        }
    write_sources_yml(workspace, sorted(counts))
    return {"workspace": str(workspace), "row_counts": counts}
