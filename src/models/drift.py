"""Mô hình phát hiện thay đổi cấu trúc nguồn (CLAUDE.md bản 2, giai đoạn 5)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ChangeType = Literal[
    "column_added",
    "type_widened",
    "type_narrowed",
    "type_incompatible",
    "column_removed",
    "nullable_changed",
    "nullable_tightened",
    "table_removed",
    "possible_rename",
    "stat_null_increase",
    "stat_rowcount",
    "stat_new_shape",
    "stat_range_shift",
]
Severity = Literal["info", "warning", "breaking"]
ChangeStatus = Literal["open", "acknowledged", "resolved"]
SEVERITY_ORDER = {"info": 0, "warning": 1, "breaking": 2}


class ColumnMeta(BaseModel):
    """Một cột trong ảnh chụp: kiểu chuẩn hóa, cho phép rỗng, vị trí."""

    type: str
    nullable: bool = True
    position: int = 0


class ChangeDraft(BaseModel):
    """Một thay đổi vừa phát hiện (chưa lưu)."""

    table: str
    change_type: ChangeType
    severity: Severity
    detail: str
    column: str = ""
    hint: str = ""  # vd `possible_rename: old → new`


class SchemaChangeView(BaseModel):
    """Một thay đổi đã lưu, cho API/web. Chỉ cấu trúc và số đếm, không có giá trị dữ liệu."""

    id: int
    source_id: int
    source_name: str = ""
    table: str
    from_version: int
    to_version: int
    change_type: ChangeType
    severity: Severity
    detail: str
    hint: str = ""
    detected_at: datetime
    status: ChangeStatus
    acknowledged_by: str = ""
    affected_pipelines: list[dict] = Field(default_factory=list)  # [{run_id, target}] dùng cột bị đổi


class DriftReport(BaseModel):
    """Kết quả một lần kiểm tra: số nguồn đã kiểm, thay đổi MỚI, và các thay đổi `breaking` đang mở."""

    checked_sources: int = 0
    unreachable: list[str] = Field(default_factory=list)  # tên nguồn không kiểm được (mất kết nối, thiếu bí mật)
    new_changes: list[SchemaChangeView] = Field(default_factory=list)
    open_breaking: list[SchemaChangeView] = Field(default_factory=list)
    warnings: list[SchemaChangeView] = Field(default_factory=list)
    tables: dict[str, dict] = Field(
        default_factory=dict, exclude=True
    )  # cấu trúc hiện tại theo nguồn (cho state lần chạy)

    @property
    def blocked(self) -> bool:
        return bool(self.open_breaking)


class DiffRow(BaseModel):
    """Một dòng của hình so sánh trước/sau: một cột và trạng thái của nó."""

    name: str
    before_type: str = ""
    after_type: str = ""
    status: Literal["same", "added", "removed", "changed", "renamed_from", "renamed_to"] = "same"
    note: str = ""


class ChangeDiff(BaseModel):
    """Hình trực quan một thay đổi: bảng nào, cột nào đổi gì. Chỉ cấu trúc (tên cột, kiểu), không có dữ liệu."""

    change_id: int
    source_name: str = ""
    table: str
    column: str = ""
    change_type: ChangeType
    severity: Severity
    before_version: int = 0
    after_version: int = 0
    rows: list[DiffRow] = Field(default_factory=list)


class AdviceFile(BaseModel):
    """Một file của pipeline bị ảnh hưởng."""

    path: str
    role: Literal["staging", "mart", "sources", "test", "dag"]
    impact: Literal["direct", "indirect"]


class AdviceAction(BaseModel):
    """Một việc cần làm: ở đâu, làm gì."""

    where: str
    what: str


class Advice(BaseModel):
    """Đề xuất sửa pipeline cho một thay đổi cấu trúc. Phần chắc chắn do CODE dựng; `ai_text` (Gemini) chỉ diễn giải thêm, tùy chọn."""

    change_id: int
    needs_pipeline_change: bool
    headline: str
    run_id: str = ""
    files: list[AdviceFile] = Field(default_factory=list)
    actions: list[AdviceAction] = Field(default_factory=list)
    ai_text: str = ""
    ai_source: Literal["", "gemini", "mock", "unavailable"] = ""


# ---------- Bản vá nhanh (patch fast-path) ----------

PatchAction = Literal["none", "code", "llm", "ask", "blocked"]


class FixStep(BaseModel):
    """Một bước sửa tất định trên SQL: đổi tên cột tham chiếu, hoặc ép kiểu về kiểu cũ ở lớp staging."""

    kind: Literal["rename", "cast"]
    old: str = ""  # rename: tên cột cũ
    new: str = ""  # rename: tên cột mới
    column: str = ""  # cast: cột cần ép
    sql_type: str = ""  # cast: kiểu SQL đích (kiểu cũ của cột)


class PatchOption(BaseModel):
    value: str
    label: str


class PatchQuestion(BaseModel):
    """Câu hỏi trắc nghiệm cho phần chỉ người mới biết (cột nào thay cột bị xóa?). Chỉ tên cột và kiểu."""

    id: str
    text: str
    options: list[PatchOption]


class PatchItem(BaseModel):
    """Cách xử lý một thay đổi cấu trúc trong bản vá: không cần sửa / sửa bằng code / cần AI / cần người chọn / không vá được."""

    change_id: int
    source_id: int
    change_type: str
    table: str
    column: str = ""
    action: PatchAction
    summary: str
    files: list[str] = Field(default_factory=list)  # file SQL sẽ bị sửa (staging + test đọc đúng bảng đó)
    steps: list[FixStep] = Field(default_factory=list)
    question: PatchQuestion | None = None


class PatchPlan(BaseModel):
    """Kế hoạch bản vá dựng bằng code (0 token) TRƯỚC khi tạo run: người xem được cái gì tự sửa, cái gì cần AI, cái gì cần họ chọn."""

    run_id: str
    items: list[PatchItem] = Field(default_factory=list)
    ready: bool = True  # không còn câu hỏi chưa trả lời, không có thay đổi không vá được
    code_fixes: int = 0
    llm_items: int = 0
    questions: int = 0  # câu hỏi chưa trả lời
    blocked: int = 0
    estimate: str = ""
