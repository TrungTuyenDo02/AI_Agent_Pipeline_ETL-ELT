"""Mô hình sổ nguồn dữ liệu: phòng ban, nguồn, quyền xem thêm, mức truy cập dữ liệu của LLM (CLAUDE.md bản 2, giai đoạn 3).

`secret_ref` chỉ là TÊN tham chiếu (ví dụ `conn_orders_db`), không bao giờ chứa mật khẩu hay chuỗi kết nối; giá trị thật chỉ
được giải ở lớp kết nối (`src/services/secrets.py`).
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SourceKind = Literal["file", "duckdb", "postgres"]
Sensitivity = Literal["low", "medium", "high"]
LLMAccess = Literal["schema_only", "profile", "masked_sample"]
Role = Literal["engineer", "reviewer", "admin"]

LLM_ACCESS_ORDER: tuple[LLMAccess, ...] = ("schema_only", "profile", "masked_sample")
# Độ nhạy cảm → mức truy cập tối đa của LLM: high chỉ cấu trúc; medium tới thống kê; low mới được xem dòng đã che.
MAX_ACCESS_BY_SENSITIVITY: dict[str, LLMAccess] = {"high": "schema_only", "medium": "profile", "low": "masked_sample"}
ALL_TABLES = "*"
SECRET_REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
COLUMN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,127}$")
ACCESS_TEXT = {
    "schema_only": "AI chỉ thấy cấu trúc (tên bảng, tên cột, kiểu)",
    "profile": "AI thấy thống kê, không thấy dòng thật",
    "masked_sample": "AI thấy vài dòng đã che",
}


def cap_access(sensitivity: str, requested: str) -> LLMAccess:
    """Mức truy cập thực sự dùng: thấp hơn trong (mức yêu cầu, trần theo độ nhạy cảm)."""
    cap = MAX_ACCESS_BY_SENSITIVITY[sensitivity]
    return LLM_ACCESS_ORDER[min(LLM_ACCESS_ORDER.index(requested), LLM_ACCESS_ORDER.index(cap))]  # type: ignore[arg-type]


def access_problem(sensitivity: str, requested: str) -> str:
    """Lý do cấu hình mức truy cập bị từ chối (chuỗi rỗng = hợp lệ)."""
    if cap_access(sensitivity, requested) != requested:
        cap = MAX_ACCESS_BY_SENSITIVITY[sensitivity]
        return (
            f"Nguồn độ nhạy cảm '{sensitivity}' chỉ cho AI xem tối đa mức '{cap}' ({ACCESS_TEXT[cap]}); "
            f"không thể đặt '{requested}'."
        )
    return ""


class Department(BaseModel):
    """Phòng ban: ranh giới quyền xem nguồn mặc định."""

    id: int
    name: str


class DataSource(BaseModel):
    """Một nguồn dữ liệu đã đăng ký. `allowed_tables` = ["*"] nghĩa là mọi bảng của nguồn."""

    id: int
    name: str
    department_id: int
    kind: SourceKind
    secret_ref: str = ""
    allowed_tables: list[str] = Field(default_factory=list)
    sensitivity: Sensitivity = "medium"
    llm_access: LLMAccess = "profile"
    restricted_columns: list[str] = Field(default_factory=list)
    enabled: bool = True

    def allows_table(self, table: str) -> bool:
        """Bảng có nằm trong danh sách được phép (so không phân biệt hoa/thường)."""
        tables = {t.lower() for t in self.allowed_tables}
        return ALL_TABLES in tables or table.lower() in tables

    @property
    def effective_llm_access(self) -> LLMAccess:
        """Mức truy cập đã hạ về trần theo độ nhạy cảm (phòng thủ lần hai, dù cấu hình sai)."""
        return cap_access(self.sensitivity, self.llm_access)


class SourceGrant(BaseModel):
    """Cấp thêm quyền xem một nguồn cho một người hoặc cả một phòng ban (đúng một trong hai)."""

    id: int
    source_id: int
    user_id: int | None = None
    department_id: int | None = None


class UserContext(BaseModel):
    """Người dùng đã được xác định (từ phiên đăng nhập, hoặc tên tin cậy của CLI) kèm phòng ban để lọc nguồn."""

    name: str
    role: Role = "engineer"
    user_id: int | None = None
    department_id: int | None = None


class SourceView(DataSource):
    """Nguồn trả cho web: thêm tên phòng ban và mô tả mức truy cập bằng lời. `secret_ref` chỉ Admin thấy."""

    department_name: str = ""
    access_text: str = ""
    llm_access_effective: LLMAccess = "profile"


def _clean_list(values: list[str], pattern: re.Pattern | None = None) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        text = value.strip()
        if text and (pattern is None or pattern.fullmatch(text) or text == ALL_TABLES):
            seen[text] = None
        elif text:
            raise ValueError(f"Tên '{text[:40]}' không hợp lệ (chỉ chữ, số, gạch dưới, dấu chấm).")
    return list(seen)


class SourceFields(BaseModel):
    """Trường chung khi đăng ký/sửa nguồn (kiểm tra cú pháp; luật liên trường kiểm ở `source_registry`)."""

    name: str | None = Field(default=None, max_length=80)
    department_id: int | None = None
    kind: SourceKind | None = None
    secret_ref: str | None = Field(default=None, max_length=64)
    allowed_tables: list[str] | None = Field(default=None, max_length=500)
    sensitivity: Sensitivity | None = None
    llm_access: LLMAccess | None = None
    restricted_columns: list[str] | None = Field(default=None, max_length=500)
    enabled: bool | None = None

    @field_validator("secret_ref")
    @classmethod
    def _secret_ref_is_a_name(cls, value: str | None) -> str | None:
        if value and not SECRET_REF_RE.fullmatch(value):
            raise ValueError(
                "secret_ref chỉ là tên tham chiếu (chữ, số, gạch dưới, bắt đầu bằng chữ), không phải mật khẩu hay chuỗi kết nối."
            )
        return value

    @field_validator("allowed_tables")
    @classmethod
    def _tables(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_list(value, COLUMN_RE)

    @field_validator("restricted_columns")
    @classmethod
    def _columns(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_list(value, COLUMN_RE)


class CreateSourceBody(SourceFields):
    """Admin đăng ký nguồn mới."""

    name: str = Field(min_length=2, max_length=80)
    department_id: int
    kind: SourceKind


class UpdateSourceBody(SourceFields):
    """Admin sửa nguồn (trường nào bỏ trống thì giữ nguyên)."""


class DepartmentBody(BaseModel):
    """Admin tạo phòng ban."""

    name: str = Field(min_length=2, max_length=80)
