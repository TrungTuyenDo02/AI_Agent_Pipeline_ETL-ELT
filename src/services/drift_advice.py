"""Hình trực quan và đề xuất sửa pipeline cho một thay đổi cấu trúc nguồn (giai đoạn 5, mở rộng).

- `change_diff`: so cột trước/sau của bảng bị đổi (từ hai phiên bản ảnh chụp), để web vẽ "bảng nào, cột nào, đổi gì". Chỉ cấu trúc.
- `suggest`: pipeline nào bị ảnh hưởng, FILE nào cần sửa và sửa gì. Phần chắc chắn do CODE dựng (phân tích SQL của lần chạy đã sinh + luật theo
  loại thay đổi). LLM rẻ (Gemini, `drift_advice` trong config/models.yaml) chỉ diễn giải thêm, chỉ khi người bấm, nhận cấu trúc chứ không có dữ liệu;
  lỗi gọi LLM thì vẫn trả phần của code.
Không bao giờ tự tạo run hay tự sửa: người bấm "Đề xuất bản vá" ở trang Thay đổi cấu trúc mới tạo lần chạy vá.
"""

import logging
import re

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.agents.tools.sql_tools import SOURCE_RE
from src.config import ADVICE_TASK, get_settings
from src.models.drift import Advice, AdviceAction, AdviceFile, ChangeDiff, DiffRow, SchemaChangeView
from src.models.llm_outputs import AdviceOutput
from src.services import llm, schema_drift
from src.services.auth import get_engine

logger = logging.getLogger(__name__)
REF_RE = re.compile(r"ref\(\s*['\"]([\w.]+)['\"]\s*\)")
NEEDS_EDIT = {
    "possible_rename",
    "column_removed",
    "type_incompatible",
    "type_narrowed",
    "nullable_changed",
    "table_removed",
}
RENAME_RE = re.compile(r"possible_rename:\s*(\S+)\s*→\s*(\S+)")


# ---------- Hình trước/sau ----------


def _columns(db: Session, source_id: int, table: str, version: int) -> dict[str, dict]:
    row = db.scalar(
        select(schema_drift.SourceSchemaSnapshot).where(
            schema_drift.SourceSchemaSnapshot.source_id == source_id,
            schema_drift.SourceSchemaSnapshot.table_name == table,
            schema_drift.SourceSchemaSnapshot.version == version,
        )
    )
    return dict(row.columns) if row else {}


def build_rows(before: dict[str, dict], after: dict[str, dict], view: SchemaChangeView) -> list[DiffRow]:
    """Hợp hai danh sách cột thành các dòng so sánh, theo vị trí cột; cột đổi tên (nghi) nối với nhau."""
    rename = RENAME_RE.search(view.hint or "")
    old_name, new_name = (rename.group(1), rename.group(2)) if rename else ("", "")
    rows: list[DiffRow] = []
    names = sorted({*before, *after}, key=lambda n: (before.get(n) or after.get(n))["position"])
    for name in names:
        b, a = before.get(name), after.get(name)
        if b and a:
            changed = b["type"] != a["type"] or b.get("nullable", True) != a.get("nullable", True)
            note = ""
            if b["type"] != a["type"]:
                note = f"kiểu {b['type']} → {a['type']}"
            elif changed:
                note = "cho phép rỗng đổi" if a.get("nullable", True) else "thành NOT NULL"
            rows.append(
                DiffRow(
                    name=name,
                    before_type=b["type"],
                    after_type=a["type"],
                    status="changed" if changed else "same",
                    note=note,
                )
            )
        elif b:
            status = "renamed_from" if name == old_name else "removed"
            rows.append(
                DiffRow(
                    name=name,
                    before_type=b["type"],
                    status=status,
                    note=f"đổi tên thành {new_name}" if rename and name == old_name else "bị xóa",
                )
            )
        elif a:
            status = "renamed_to" if name == new_name else "added"
            rows.append(
                DiffRow(
                    name=name,
                    after_type=a["type"],
                    status=status,
                    note=f"trước đây là {old_name}" if rename and name == new_name else "cột mới",
                )
            )
    return rows


def columns_before_after(view: SchemaChangeView) -> tuple[dict[str, dict], dict[str, dict]]:
    """Cột của bảng ở phiên bản trước và sau thay đổi (từ hai ảnh chụp đã lưu); bảng bị xóa thì bên "sau" rỗng."""
    with Session(get_engine()) as db:
        before = _columns(db, view.source_id, view.table, view.from_version)
        after = {} if view.change_type == "table_removed" else _columns(db, view.source_id, view.table, view.to_version)
    return before, after


def change_diff(change_id: int) -> ChangeDiff | None:
    """Hình so sánh cột trước/sau của một thay đổi; thay đổi thống kê (không đổi cấu trúc) trả danh sách dòng rỗng."""
    view = schema_drift.get_change(change_id)
    if view is None:
        return None
    column = schema_drift._column_of_view(view)  # noqa: SLF001
    rows: list[DiffRow] = []
    if not view.change_type.startswith("stat_"):
        rows = build_rows(*columns_before_after(view), view)
    return ChangeDiff(
        change_id=view.id, source_name=view.source_name, table=view.table, column=column, change_type=view.change_type,
        severity=view.severity, before_version=view.from_version, after_version=view.to_version, rows=rows,
    )  # fmt: skip


# ---------- Đề xuất sửa pipeline ----------


def _role(path: str) -> str:
    if path.startswith("models/staging/"):
        return "staging"
    if path.startswith("models/marts/"):
        return "mart"
    if path.endswith("sources.yml"):
        return "sources"
    if path.startswith("dags/"):
        return "dag"
    return "test"


def _uses_column(sql: str, column: str) -> bool:
    return bool(column) and re.search(rf"\b{re.escape(column)}\b", sql, re.IGNORECASE) is not None


def affected_files(
    code_files: dict[str, str], test_files: dict[str, str], view: SchemaChangeView, column: str
) -> list[AdviceFile]:
    """File của pipeline đọc bảng bị đổi (và dùng cột đó): staging đọc trực tiếp bảng raw, mart đọc gián tiếp qua `ref`."""
    files: list[AdviceFile] = []
    direct_models: set[str] = set()
    for path, sql in sorted(code_files.items()):
        if not path.endswith(".sql") or not path.startswith("models/staging/"):
            continue
        tables = {m.group(2) for m in SOURCE_RE.finditer(sql)}
        if view.table in tables and (not column or _uses_column(sql, column) or view.change_type == "table_removed"):
            files.append(AdviceFile(path=path, role="staging", impact="direct"))
            direct_models.add(path.rsplit("/", 1)[-1].removesuffix(".sql"))
    for path, sql in sorted(code_files.items()):
        if path.startswith("models/marts/") and direct_models & set(REF_RE.findall(sql)):
            files.append(AdviceFile(path=path, role="mart", impact="indirect"))
    if files:
        files.append(AdviceFile(path="models/sources.yml", role="sources", impact="direct"))
        files += [
            AdviceFile(path=path, role="test", impact="direct")
            for path, sql in sorted(test_files.items())
            if path.endswith("_castable.sql") and view.table in sql and (not column or _uses_column(sql, column))
        ]
    return files


def _where(files: list[AdviceFile], role: str) -> str:
    paths = [f.path for f in files if f.role == role]
    return ", ".join(paths) if paths else ""


def build_actions(view: SchemaChangeView, column: str, files: list[AdviceFile]) -> list[AdviceAction]:
    """Việc cần làm theo loại thay đổi (luật cố định, 0 token)."""
    stg, mart, src, tests = (_where(files, r) for r in ("staging", "mart", "sources", "test"))
    kind, table = view.change_type, view.table
    rename = RENAME_RE.search(view.hint or "")
    out: list[AdviceAction] = []

    def add(where: str, what: str) -> None:
        if where:
            out.append(AdviceAction(where=where, what=what))

    if kind == "possible_rename" and rename:
        add(
            stg,
            f"Đổi tham chiếu cột {rename.group(1)} thành {rename.group(2)} (nếu đúng là đổi tên) trong phần đọc {table}.",
        )
        add(src, f"Cập nhật tên cột kỳ vọng {rename.group(1)} → {rename.group(2)}.")
        add(tests, "Cập nhật tên cột trong test ép kiểu.")
    elif kind == "column_removed":
        add(stg, f"Bỏ hoặc thay cột {column} bằng cột khác trong phần đọc {table}.")
        add(mart, f"Kiểm tra chỉ số/nhóm nào dùng {column} và sửa lại.")
        add(src, f"Xóa cột {column} khỏi khai báo nguồn.")
    elif kind in ("type_incompatible", "type_narrowed"):
        add(
            stg,
            f"Sửa biểu thức đọc/ép kiểu của {column} cho kiểu mới ({view.detail.split('đổi kiểu')[-1].split('(')[0].strip()}).",
        )
        add(src, f"Cập nhật data_type kỳ vọng của {column}.")
        add(tests, f"Cập nhật test ép kiểu cho {column}.")
    elif kind == "nullable_changed":
        add(stg, f"Xử lý giá trị rỗng của {column} (vd coalesce) vì cột nay cho phép rỗng.")
        add(src, f"Bỏ test not_null của {column} nếu có.")
    elif kind == "table_removed":
        add(stg, f"Đổi sang bảng nguồn thay thế hoặc ngừng phần đọc {table}.")
        add(mart, "Kiểm tra bảng đích còn đủ nguồn.")
    elif kind == "type_widened":
        add(src, f"Cập nhật data_type kỳ vọng của {column}; thường không cần sửa model.")
    elif kind == "stat_null_increase":
        add(stg or "pipeline", f"{column} rỗng nhiều hơn: kiểm tra bộ lọc/JOIN có làm mất dòng; hỏi đội nguồn vì sao.")
    elif kind == "stat_new_shape":
        add(stg or "pipeline", f"Có dạng giá trị mới ở {column}: bổ sung định dạng vào phép đọc.")
    elif kind == "stat_range_shift":
        add(
            stg or "pipeline",
            f"Khoảng giá trị của {column} lệch mạnh: xác nhận đơn vị với đội nguồn rồi quy đổi nếu cần.",
        )
    elif kind == "stat_rowcount":
        add(stg or "pipeline", f"Số dòng của {table} lệch nhiều: kiểm tra nguồn nạp thiếu/thừa trước khi chạy tiếp.")
    return out


def _headline(view: SchemaChangeView, files: list[AdviceFile], needs: bool) -> str:
    if not files:
        return "Chưa có pipeline đã sinh nào dùng bảng/cột này, không cần sửa pipeline."
    if needs:
        return (
            "Cần sửa pipeline: "
            + str(len([f for f in files if f.impact == "direct" and f.role != "sources"]))
            + " file đọc trực tiếp bảng bị đổi."
        )
    return "Thường không cần sửa model; chỉ kiểm tra lại như gợi ý bên dưới."


def ai_explain(
    view: SchemaChangeView, column: str, files: list[AdviceFile], actions: list[AdviceAction]
) -> tuple[str, str]:
    """Lời diễn giải của model rẻ (Gemini) → (văn bản, nguồn). Lỗi gọi (thiếu khóa, mạng, sai định dạng) thì trả ("", "unavailable")."""
    variables = {
        "change": llm.to_json(
            {
                "type": view.change_type,
                "severity": view.severity,
                "table": view.table,
                "column": column,
                "detail": view.detail,
            }
        ),
        "files": llm.to_json([f.model_dump() for f in files]),
        "actions": llm.to_json([a.model_dump() for a in actions]),
    }
    try:
        response = llm.call_llm(ADVICE_TASK, variables)
        out = AdviceOutput.model_validate(llm.parse_json_output(response.text))
    except (llm.LLMOutputError, ValidationError) as exc:
        logger.warning("drift advice output invalid", extra={"error": str(exc)[:200]})
        return "", "unavailable"
    except Exception as exc:  # noqa: BLE001 — diễn giải chỉ là phần thêm: mọi lỗi gọi LLM đều không làm hỏng đề xuất của code
        logger.warning("drift advice unavailable", extra={"error": str(exc)[:200]})
        return "", "unavailable"
    text = out.summary.strip()
    if out.extra_steps:
        text += "\n" + "\n".join(f"- {s.strip()}" for s in out.extra_steps[:3])
    mock = get_settings().llm_provider == "mock"
    return text, "mock" if mock else "gemini"


def suggest(view: SchemaChangeView, run_id: str = "", use_ai: bool = False) -> Advice:
    """Đề xuất sửa pipeline cho một thay đổi, dựa trên code đã sinh của `run_id` (mặc định: lần chạy đầu tiên dùng bảng này)."""
    from src.agents import runner  # nhập muộn: runner nhập schema_drift

    column = schema_drift._column_of_view(view)  # noqa: SLF001
    run_id = run_id or next((p["run_id"] for p in view.affected_pipelines), "")
    values = runner.get_values(run_id) if run_id else {}
    files = affected_files(values.get("code_files", {}), values.get("test_files", {}), view, column)
    needs = bool(files) and view.change_type in NEEDS_EDIT
    actions = build_actions(view, column, files)
    advice = Advice(
        change_id=view.id,
        needs_pipeline_change=needs,
        headline=_headline(view, files, needs),
        run_id=run_id,
        files=files,
        actions=actions,
    )
    if use_ai and (files or actions):
        advice.ai_text, advice.ai_source = ai_explain(view, column, files, actions)  # type: ignore[assignment]
    return advice
