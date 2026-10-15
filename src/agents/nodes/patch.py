"""Bản vá nhanh khi nguồn đổi cấu trúc (xem `src/services/patch_plan.py`): ba node code thuần, 0 token.

Run vá bắt đầu từ `patch_start` thay vì `input_gate`, mang sẵn đặc tả đã duyệt, câu trả lời J1, lựa chọn J1b và code của lần chạy gốc, nên không
hỏi lại và không lập kế hoạch lại. Luồng: patch_start → ingest → profiler → patch_apply → (codegen chỉ khi còn phần cần AI) → testgen → V1 → V2 →
patch_verify → package → J2. Không có E4 (code gốc đã tối ưu) và không có Vs (chính bản vá là sự xác nhận cấu trúc mới).
"""

import logging
from pathlib import Path

import duckdb

from src.agents.nodes.common import sandbox_db, spec_of
from src.agents.state import PipelineState
from src.agents.tools.duckdb_tools import connect_read
from src.config import get_settings
from src.models.drift import PatchItem, PatchPlan
from src.models.schemas import RunStatus
from src.services import patch_plan, schema_drift
from src.services import source_registry as registry
from src.services.schema_watch import snapshot_from_profile

logger = logging.getLogger(__name__)
SANDBOX_NAME = "sandbox.duckdb"


def patch_start_node(state: PipelineState) -> dict:
    """Chụp cấu trúc hiện tại của các nguồn pipeline dùng (để J2 kiểm lại xem cấu trúc có đổi tiếp không)."""
    drift: dict = {"checked": False}
    if get_settings().database_url:
        used = {s.name for s in spec_of(state).sources}
        catalog = state.get("source_catalog", [])
        ids = {i["source_id"] for i in catalog if i["name"] in used and i.get("source_id") is not None}
        user = registry.user_context(state.get("requester", ""))
        sources = [s for s in registry.get_visible_sources(user) if s.enabled and s.id in ids]
        drift = {"checked": True, "unreachable": [], "warnings": [], "tables": schema_drift.run_tables(sources)}
    return {"status": RunStatus.RUNNING.value, "drift": drift, "plan_rounds": 0}


def patch_apply_node(state: PipelineState) -> dict:
    """Áp các bản sửa tất định theo kế hoạch đã dựng lúc tạo run. Phần không sửa được an toàn → lời nhắc cho Codegen (chỉ tên cột/kiểu/file)."""
    patch = dict(state.get("patch") or {})
    plan = PatchPlan.model_validate(patch.get("plan") or {"run_id": patch.get("parent", "")})
    code, tests, applied, leftover, already_ok = patch_plan.apply_plan(
        state.get("code_files", {}), state.get("test_files", {}), plan
    )
    tests = {
        path: sql for path, sql in tests.items() if not path.endswith("_castable.sql")
    }  # Testgen dựng lại theo hồ sơ MỚI
    llm_items: list[PatchItem] = [i for i in plan.items if i.action == "llm"] + leftover
    if llm_items:
        tests = {}  # code đổi nghĩa thì đáp án kiểm tra cũng phải tính lại: Testgen (mù code) viết lại theo đặc tả và hồ sơ mới
    patch |= {
        "applied": applied,
        "already_ok": already_ok,
        "llm_items": [i.model_dump() for i in llm_items],
        "llm_files": sorted({f for i in llm_items for f in i.files}),
    }
    return {
        "code_files": code,
        "test_files": tests,
        "patch": patch,
        "rescue_hint": patch_plan.llm_hint(llm_items) if llm_items else "",
        "schema_snapshot": snapshot_from_profile(state.get("profile", {}), state.get("source_catalog", [])),
    }


def _mart_rows(db: Path, target: str) -> list[tuple]:
    with connect_read(db) as con:
        return con.execute(f'SELECT * FROM main."{target}" ORDER BY ALL').fetchall()


def compare_marts(parent_db: Path, new_db: Path, target: str) -> dict:
    """So bảng đích của bản vá với lần chạy gốc (đo bằng code). Nguồn thật có thể đã đổi dữ liệu nên khác biệt chỉ là bằng chứng cho người duyệt."""
    if not parent_db.exists():
        return {"compared": False, "note": "Không còn dữ liệu chạy thử của lần chạy gốc để so sánh."}
    try:
        before, after = _mart_rows(parent_db, target), _mart_rows(new_db, target)
    except duckdb.Error as exc:
        logger.warning("patch compare failed", extra={"error": str(exc)[:200]})
        return {"compared": False, "note": "Không so sánh được bảng đích với lần chạy gốc."}
    return {
        "compared": True,
        "same": before == after,
        "rows_before": len(before),
        "rows_after": len(after),
        "differing_rows": len(set(before) ^ set(after)),
    }


def patch_verify_node(state: PipelineState) -> dict:
    """Sau V2: bảng đích mới so với bảng đích của lần chạy gốc."""
    patch = dict(state.get("patch") or {})
    parent_db = Path(patch.get("parent_workspace") or "") / SANDBOX_NAME
    patch["regression"] = compare_marts(parent_db, sandbox_db(state), spec_of(state).target)
    return {"patch": patch}
