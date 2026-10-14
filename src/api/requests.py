"""Khuôn dữ liệu vào/ra của API (chỉ tầng API; hợp đồng giữa các agent nằm ở `src/models/`)."""

from typing import Literal

from pydantic import BaseModel, Field

from src.models.schemas import RunRecord


class CreateRunBody(BaseModel):
    """Yêu cầu nghiệp vụ bằng lời."""

    request_text: str = Field(min_length=5, max_length=4000, examples=["Gộp đơn hàng 3 nguồn, tính doanh thu ngày"])


class AnswerBody(BaseModel):
    """Câu trả lời J1: id câu hỏi → lựa chọn (đúng nguyên văn); câu chọn nhiều (`multiple`) nhận danh sách."""

    answers: dict[str, str | list[str]] = Field(min_length=1)


class PlanBody(BaseModel):
    """Quyết định J1b: đồng ý kế hoạch, hoặc yêu cầu sửa kèm ghi chú cho Planner."""

    decision: Literal["approve", "revise"]
    note: str = Field(default="", max_length=2000)


class ReviewBody(BaseModel):
    """Quyết định J2; từ chối thì phải có ghi chú cho Coder."""

    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=2000)


class SchemaBody(BaseModel):
    """Xác nhận khi nguồn có cột bị xóa/đổi tên: chạy tiếp (kèm cặp đổi tên đã xác nhận) hoặc dừng."""

    action: Literal["continue", "abort"]
    renames: dict[str, str] = Field(default_factory=dict)  # cột cũ → cột mới, chỉ trong danh sách nghi vấn


class RescueBody(BaseModel):
    """Cứu hộ: gợi ý cho Coder rồi thử lại, hoặc dừng."""

    action: Literal["retry", "abort"]
    hint: str = Field(default="", max_length=2000)


class ErrorFixBody(BaseModel):
    """Duyệt một mục sổ lỗi kèm cách sửa."""

    fix: str = Field(default="", max_length=2000)


class Accepted(BaseModel):
    """Đã nhận, đang chạy nền."""

    run_id: str
    status: str
    message: str


class RunDetail(BaseModel):
    """Chi tiết một lần chạy cho màn hình web."""

    record: RunRecord
    busy: bool
    pending: dict | None
    events: list[dict]
    spec: dict
    answered: list[dict]  # các câu J1 đã trả lời (câu hỏi + lựa chọn)
    evidence: dict
    optimization: dict
    sandbox: dict
    code_notes: list[str]
    test_notes: list[str]
    stages: list[dict] = []  # đường ống E/V/J: trạng thái từng nút từ dữ liệu thật (src/agents/stages.py)
    usage: dict = {}  # token/chi phí/thời gian LLM theo node + tỉ lệ trúng cache (services/cost.usage_breakdown)
    # node đang chạy: {node, label, stage, started_at, elapsed_s, typical_s, samples, activity}; None khi rảnh.
    # typical_s là trung vị thời gian ĐO THẬT các lần trước (None khi chưa đủ mẫu); activity là mô tả, không phải log đo.
    current: dict | None = None
    queue_position: int | None = None  # số lần chạy đứng trước trong hàng (0 = đang chạy); None khi không xếp hàng
    schema_report: dict = {}  # mục 8: cấu trúc nguồn so với bản đã duyệt + đề xuất sửa
    schema_decision: dict = {}  # Engineer đã xác nhận gì khi có cột bị xóa/đổi tên
    value_filters: list[dict] = []  # mục 9: điều kiện cứng theo giá trị (tô sáng ở màn duyệt)
    reconciliation: list[dict] = []  # mục 9: số dòng vào → ra từng model staging
    retryable: bool = False  # lần chạy lỗi nhưng còn checkpoint: có nút "Chạy lại từ bước lỗi"


class RunFiles(BaseModel):
    """Code + test hiện tại và bộ file của vòng duyệt trước (để xem diff)."""

    code_files: dict[str, str]
    test_files: dict[str, str]
    previous_files: dict[str, str]
