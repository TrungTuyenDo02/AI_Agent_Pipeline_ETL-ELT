"""Bản vá nhanh khi nguồn đổi cấu trúc: lập kế hoạch vá bằng code, áp dụng bản sửa tất định, dựng trạng thái khởi đầu cho run vá.

Vấn đề cũ: "Đề xuất bản vá" tạo một run MỚI từ một đoạn văn rồi cho đi lại từ đầu (cửa kiểm tra → Planner → hỏi làm rõ → duyệt kế hoạch →
sinh lại toàn bộ code). Người dùng bị hỏi lại những điều đã trả lời, tốn token cho việc không cần LLM.

Cách làm của một DE kỳ cựu, áp dụng ở đây:
1. Đặc tả đã duyệt là hợp đồng: nghiệp vụ không đổi, chỉ nguồn đổi → run vá MANG THEO đặc tả, câu trả lời J1, lựa chọn J1b và bộ code cũ.
2. Phân loại từng thay đổi (`build_plan`, 0 token): không cần sửa / sửa bằng code (đổi tên cột, ép về kiểu cũ ở staging) / cần AI / cần người chọn
   (cột nào thay cột bị xóa?) / không vá được (bảng bị xóa). Người xem kế hoạch này TRƯỚC khi tạo run.
3. Chỉ phần còn mơ hồ mới đi tới LLM, với ngữ cảnh là tên cột/kiểu và đúng các file cần sửa, không phải cả pipeline.
4. Kiểm chứng như mọi bản code (V1, V2) rồi so bảng đích với lần chạy gốc (`patch_verify`): đổi tên thuần phải ra kết quả y hệt.
"""

import re
from collections.abc import Callable

from src.agents.tools import drift_fix
from src.models.drift import FixStep, PatchItem, PatchOption, PatchPlan, PatchQuestion, SchemaChangeView
from src.services import schema_drift

ColumnsOf = Callable[
    [SchemaChangeView], tuple[dict[str, dict], dict[str, dict]]
]  # (cột trước, cột sau) của bảng bị đổi
RENAME_RE = re.compile(r"possible_rename:\s*(\S+)\s*→\s*(\S+)")
MAX_ITEMS = 50
USE_PREFIX = "use:"
DROP = "drop"
NO_CODE_TEXT = {
    "column_added": "Cột mới không vào pipeline vì code chọn cột tường minh; không cần sửa.",
    "type_widened": "Kiểu được mở rộng an toàn; thường không cần sửa model, chỉ cập nhật bản chuẩn.",
    "nullable_changed": "Cột nay cho phép rỗng; test not_null (nếu có) sẽ báo nếu có dòng rỗng.",
    "nullable_tightened": "Cột thành NOT NULL: chặt hơn, không làm hỏng pipeline.",
}


def _base(view: SchemaChangeView, column: str) -> dict:
    return {
        "change_id": view.id, "source_id": view.source_id, "change_type": view.change_type, "table": view.table, "column": column,
    }  # fmt: skip


def _none(view: SchemaChangeView, column: str, summary: str) -> PatchItem:
    return PatchItem(**_base(view, column), action="none", summary=summary)


def _question(view: SchemaChangeView, column: str, before: dict, after: dict) -> PatchQuestion:
    """Câu hỏi trắc nghiệm: dùng cột MỚI nào thay cột cũ, hoặc bỏ cột khỏi pipeline. Chỉ tên cột và kiểu."""
    rename = RENAME_RE.search(view.hint or "")
    suspect = rename.group(2) if rename else ""
    fresh = sorted((c for c in after if c not in before), key=lambda c: (c != suspect, after[c].get("position", 0)))
    options = [
        PatchOption(
            value=f"{USE_PREFIX}{c}",
            label=f"Dùng cột {c} thay cho {column} (kiểu {after[c]['type']})"
            + (" — nghi là cột đã đổi tên" if c == suspect else ""),
        )
        for c in fresh
    ]
    options.append(PatchOption(value=DROP, label=f"Bỏ cột {column} khỏi pipeline (cần AI sửa file, có tốn token)"))
    text = f"Cột {view.table}.{column} không còn ở nguồn. Cột nào thay thế nó?"
    return PatchQuestion(id=str(view.id), text=text, options=options)


def _answered_steps(column: str, new: str, before: dict, after: dict) -> list[FixStep]:
    steps = [FixStep(kind="rename", old=column, new=new)]
    old_type, new_type = (before.get(column) or {}).get("type", ""), (after.get(new) or {}).get("type", "")
    if old_type and new_type and old_type != new_type and old_type in drift_fix.SQL_TYPES:
        steps.append(FixStep(kind="cast", column=new, sql_type=drift_fix.SQL_TYPES[old_type]))
    return steps


def _plan_item(
    view: SchemaChangeView, files: dict[str, str], answers: dict[str, str], before: dict, after: dict
) -> PatchItem:
    kind, column = view.change_type, schema_drift._column_of_view(view)  # noqa: SLF001
    if kind.startswith("stat_"):
        return _none(view, column, "Thay đổi về thống kê, không đổi cấu trúc: xác nhận với đội nguồn, không sửa code.")
    if kind in NO_CODE_TEXT:
        return _none(view, column, NO_CODE_TEXT[kind])
    if kind == "table_removed":
        text = f"Bảng {view.table} không còn ở nguồn: cần đội nguồn hoặc người quyết định bảng thay thế; hệ thống không tự vá."
        return PatchItem(**_base(view, column), action="blocked", summary=text)
    targets = drift_fix.files_to_fix(files, view.table, column)
    if not targets:
        return _none(view, column, "Pipeline không đọc cột này trực tiếp ở staging hoặc test: không cần sửa code.")
    base = {**_base(view, column), "files": targets}
    if kind in ("type_incompatible", "type_narrowed"):
        old_type = (before.get(column) or {}).get("type", "")
        if sql_type := drift_fix.SQL_TYPES.get(old_type):
            summary = f"Ép {column} về kiểu cũ ({old_type}) ngay ở staging để phần phía sau không đổi."
            return PatchItem(
                **base, action="code", summary=summary, steps=[FixStep(kind="cast", column=column, sql_type=sql_type)]
            )
        return PatchItem(
            **base, action="llm", summary=f"Cột {column} đổi kiểu và kiểu cũ không ép ngược tự động được: AI sửa file."
        )
    # possible_rename, column_removed (cột đang được dùng ở staging/test)
    question = _question(view, column, before, after)
    answer = answers.get(str(view.id), "")
    if answer == DROP:
        return PatchItem(
            **base, action="llm", summary=f"Bỏ cột {column} khỏi pipeline: AI sửa file và các model dùng nó."
        )
    new = answer.removeprefix(USE_PREFIX) if answer.startswith(USE_PREFIX) else ""
    if new and new in after and new not in before:
        steps = _answered_steps(column, new, before, after)
        summary = f"Đổi tham chiếu {column} → {new} ở staging, giữ tên cột đầu ra {column}"
        summary += " và ép về kiểu cũ." if len(steps) > 1 else "."
        return PatchItem(**base, action="code", summary=summary, steps=steps)
    return PatchItem(**base, action="ask", summary=f"Cần bạn chọn cột thay cho {column}.", question=question)


def build_plan(
    run_id: str, values: dict, changes: list[SchemaChangeView], answers: dict[str, str], columns_of: ColumnsOf
) -> PatchPlan:
    """Kế hoạch vá cho các thay đổi đang mở ảnh hưởng tới lần chạy `run_id` (0 token, không đọc dữ liệu thật)."""
    files = {**values.get("code_files", {}), **values.get("test_files", {})}
    items = [_plan_item(c, files, answers, *columns_of(c)) for c in changes[:MAX_ITEMS]]
    count = {a: sum(i.action == a for i in items) for a in ("code", "llm", "ask", "blocked")}
    if count["blocked"]:
        estimate = "Có thay đổi không vá được tự động: cần đội nguồn."
    elif count["ask"]:
        estimate = "Chọn cột thay thế để xem ước tính."
    elif count["llm"]:
        estimate = (
            f"{count['llm']} thay đổi cần AI sửa file (một lần gọi Codegen có giới hạn file); phần còn lại 0 token."
        )
    else:
        estimate = "0 token: sửa hoàn toàn bằng code, không gọi AI."
    return PatchPlan(
        run_id=run_id, items=items, ready=not (count["ask"] or count["blocked"]), code_fixes=count["code"], llm_items=count["llm"],
        questions=count["ask"], blocked=count["blocked"], estimate=estimate,
    )  # fmt: skip


def apply_plan(
    code_files: dict[str, str], test_files: dict[str, str], plan: PatchPlan
) -> tuple[dict[str, str], dict[str, str], list[dict], list[PatchItem], list[str]]:
    """Áp các bản sửa bằng code lên bộ file của lần chạy gốc. Trả (code mới, test mới, các sửa đã áp, phần không sửa được an toàn, file đã đúng sẵn).

    File không sửa được (Jinja lạ, lỗi cú pháp, không tìm thấy tham chiếu) → mục đó chuyển sang `llm` với đúng các file đó."""
    code, tests = dict(code_files), dict(test_files)
    applied: list[dict] = []
    already_ok: list[str] = []
    leftover: list[PatchItem] = []
    for item in plan.items:
        if item.action != "code":
            continue
        failed: list[str] = []
        for path in item.files:
            store = code if path in code else tests
            result = drift_fix.rewrite(store.get(path, ""), item.table, item.steps)
            renames = any(s.kind == "rename" for s in item.steps)
            if result is None or (
                not result[1] and renames
            ):  # Jinja lạ/lỗi cú pháp, hoặc đổi tên mà không thấy tham chiếu nào
                failed.append(path)
            elif result[1]:
                store[path] = result[0]
                applied.append({"change_id": item.change_id, "file": path, "fix": "+".join(s.kind for s in item.steps)})
            else:
                already_ok.append(path)  # cột đã được ép đúng kiểu sẵn: pipeline tự phòng thủ, không cần đổi
        if failed:
            text = f"Không sửa tự động an toàn được {', '.join(failed)}: AI sửa file này theo thay đổi của cột {item.column}."
            leftover.append(item.model_copy(update={"action": "llm", "files": failed, "summary": text}))
    return code, tests, applied, leftover, sorted(set(already_ok))


def llm_hint(items: list[PatchItem]) -> str:
    """Lời nhắc cho Codegen ở các mục cần AI: chỉ tên cột/kiểu/đường dẫn file (không có dữ liệu), kèm ràng buộc giữ nguyên phần còn lại."""
    lines = [f"- {i.summary} (file: {', '.join(i.files) or 'chưa xác định'})" for i in items]
    head = "BẢN VÁ do nguồn đổi cấu trúc. Chỉ sửa các file nêu dưới đây, giữ nguyên phần còn lại và tên cột đầu ra của bảng đích:"
    return head + "\n" + "\n".join(lines)


def seed_state(parent_id: str, parent: dict, plan: PatchPlan, by: str) -> dict:
    """Trạng thái khởi đầu của run vá: mang theo đặc tả, câu trả lời, lựa chọn và code của lần chạy gốc; bỏ qua cửa kiểm tra, Planner, J1, J1b."""
    carried = {
        k: parent[k]
        for k in ("spec", "source_catalog", "answers", "answered", "plan_options", "plan_feedback")
        if k in parent
    }
    old_files = {**parent.get("code_files", {}), **parent.get("test_files", {})}
    return {
        **carried,
        "patch_of": parent_id,
        "plan_review": {"decision": "approve", "note": f"Dùng lại kế hoạch đã duyệt của {parent_id}", "by": by},
        "code_files": dict(parent.get("code_files", {})),
        "test_files": dict(parent.get("test_files", {})),
        "previous_files": old_files,  # màn duyệt J2 hiện diff so với bản gốc
        "patch": {
            "parent": parent_id,
            "plan": plan.model_dump(),
            "changes": [{"id": i.change_id, "source_id": i.source_id} for i in plan.items],
            "parent_workspace": parent.get("workspace", ""),
        },
    }
