"""Từ điển nghiệp vụ (CLAUDE.md bản 2, giai đoạn 6): thuật ngữ + từ đồng nghĩa + định nghĩa + ánh xạ tới bảng/cột hoặc biểu thức.

Chỉ Admin thêm/sửa; agent chỉ đọc. Định nghĩa là chữ do con người viết, KHÔNG chứa giá trị dữ liệu thật (không có gì để che).
"""

from pydantic import BaseModel, Field, field_validator

MAX_SYNONYMS = 10


def _clean(text: str) -> str:
    return " ".join(str(text).split())


def _clean_synonyms(values: list[str]) -> list[str]:
    out = list(dict.fromkeys(s for s in (_clean(v) for v in values) if s))
    if any(len(s) > 80 for s in out):
        raise ValueError("Mỗi từ đồng nghĩa tối đa 80 ký tự.")
    return out


class GlossaryTerm(BaseModel):
    """Một thuật ngữ. `department_id` trống = dùng chung mọi phòng ban."""

    id: int = 0
    term: str
    synonyms: list[str] = Field(default_factory=list)
    definition: str
    maps_to: str = ""
    department_id: int | None = None


class GlossaryBody(BaseModel):
    """Nội dung tạo thuật ngữ (Admin)."""

    term: str = Field(min_length=2, max_length=80)
    synonyms: list[str] = Field(default_factory=list, max_length=MAX_SYNONYMS)
    definition: str = Field(min_length=5, max_length=400)
    maps_to: str = Field(default="", max_length=300)
    department_id: int | None = Field(default=None, ge=1)

    @field_validator("term", "definition", "maps_to")
    @classmethod
    def _tidy(cls, value: str) -> str:
        return _clean(value)

    @field_validator("synonyms")
    @classmethod
    def _tidy_synonyms(cls, values: list[str]) -> list[str]:
        return _clean_synonyms(values)


class UpdateGlossaryBody(BaseModel):
    """Sửa thuật ngữ: chỉ các trường gửi lên mới đổi. `department_id=0` = chuyển thành dùng chung."""

    term: str | None = Field(default=None, min_length=2, max_length=80)
    synonyms: list[str] | None = Field(default=None, max_length=MAX_SYNONYMS)
    definition: str | None = Field(default=None, min_length=5, max_length=400)
    maps_to: str | None = Field(default=None, max_length=300)
    department_id: int | None = Field(default=None, ge=0)

    @field_validator("term", "definition", "maps_to")
    @classmethod
    def _tidy(cls, value: str | None) -> str | None:
        return None if value is None else _clean(value)

    @field_validator("synonyms")
    @classmethod
    def _tidy_synonyms(cls, values: list[str] | None) -> list[str] | None:
        return None if values is None else _clean_synonyms(values)
