"""Hợp đồng bằng chứng gửi Reviewer: `measured` (code đo) tách riêng `claimed` (LLM nói)."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class MeasuredItem(BaseModel):
    """Một kết quả do V-node (code tất định) đo."""

    node: str = Field(..., description="V-node đã đo, ví dụ V2 sandbox_run")
    check: str
    result: str
    passed: bool | None = None


class Evidence(BaseModel):
    """Gói bằng chứng: hai phần luôn tách biệt."""

    measured: list[MeasuredItem] = Field(default_factory=list)
    claimed: list[str] = Field(default_factory=list, description="Lời giải thích của LLM, chưa kiểm chứng")


class Finding(BaseModel):
    """Một dấu hiệu query chậm do sqlglot/EXPLAIN phát hiện."""

    rule: str
    message: str


class QueryMetrics(BaseModel):
    """Số đo thời gian chạy (trung vị của N lần, sau 1 lần khởi động)."""

    median_ms: float
    runs: int
    peak_memory_mb: float | None = None
    # Độ phân tán IQR = Q3 − Q1 (statistics.quantiles n=4, method="inclusive") của `runs` lần đo sau 1 lần khởi động.
    # None = chưa đo (dữ liệu cũ hoặc runs < 2): không đủ bằng chứng để kết luận nhanh hơn.
    spread_ms: float | None = None


class DatasetCheck(BaseModel):
    """Kết quả đối chiếu hai query trên một bộ dữ liệu."""

    dataset: str
    equal: bool
    detail: str = ""


class Bottleneck(BaseModel):
    """Một phát hiện điểm nghẽn: hiện tượng, bằng chứng (đã đo) → giả thuyết, bước kiểm tra tiếp (chưa kiểm chứng)."""

    model: str
    rank: int
    execute_ms: float | None = None
    analyzed: bool = True  # False = "chưa phân tích được" (lý do ở `unknown`)
    operator: str = ""  # toán tử tốn thời gian nhất theo EXPLAIN ANALYZE
    phenomenon: str = ""
    evidence: list[str] = Field(default_factory=list)
    hypothesis: str = ""
    next_step: str = ""
    unknown: str = ""


class PerfReport(BaseModel):
    """Đo thời gian từng model (artifact dbt) + phân tích top N model chậm nhất. Không có số đo → `measured=False` ("chưa đo")."""

    measured: bool = False
    model_total_ms: float | None = Field(
        default=None, description="Tổng thời gian execute các model (không phải thời gian thực)"
    )
    dbt_wall_ms: float | None = Field(default=None, description="Thời gian thực của một lệnh dbt build (invocation)")
    dag_wall_ms: float | None = Field(default=None, description="Thời gian thực của cả DAG Airflow; None = chưa đo")
    analysis_ms: float = Field(default=0.0, description="Chi phí phân tích (EXPLAIN ANALYZE), 0 token")
    top_n: int = 0
    findings: list[Bottleneck] = Field(default_factory=list)
    note: str = ""


class OptimizationReport(BaseModel):
    """Báo cáo E4 + V3: số liệu trước/sau và quyết định áp dụng hay giữ nguyên."""

    original_sql: str
    proposed_sql: str = ""
    findings: list[Finding] = Field(default_factory=list)
    before: QueryMetrics | None = None
    after: QueryMetrics | None = None
    improvement_pct: float | None = None
    decision: Literal["applied", "skipped"] = "skipped"
    reason: str = ""
    attempts: int = 0
    equivalence: list[DatasetCheck] = Field(default_factory=list)
    llm_cost_usd: float = 0.0
    explanation: str = Field(default="", description="Giải thích của LLM (claimed)")
    warehouse_hints: list[str] = Field(
        default_factory=list, description="Gợi ý chỉ áp dụng cho kho khác, không thực thi"
    )
    bottlenecks: PerfReport | None = None  # tùy chọn: checkpoint cũ không có


class GateCheck(BaseModel):
    """Một kiểm tra của cổng duyệt: đạt / không đạt / chưa kiểm chứng (thiếu bằng chứng, không tính là đạt)."""

    id: str
    name: str
    status: Literal["passed", "failed", "unverified"]
    reason: str = ""


class ReviewGate(BaseModel):
    """Cổng duyệt J2: chỉ mở khi cả 4 kiểm tra bắt buộc đạt. `extra` là kiểm tra bổ sung, không chặn duyệt."""

    passed: bool
    checks: list[GateCheck]
    extra: list[GateCheck] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    """Quyết định của Reviewer ở J2."""

    run_id: str
    reviewer: str
    decision: Literal["approve", "reject"]
    note: str = ""
    decided_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ErrorEntry(BaseModel):
    """Một mục trong sổ lỗi; chỉ mục `approved=True` mới được gợi ý cho Codegen."""

    id: int | None = None
    code: str
    signature: str
    description: str
    cause: str = ""
    fix: str = ""
    sql_before: str = ""
    sql_after: str = ""
    occurrences: int = 1
    approved: bool = False
    warnings: list[str] = []  # dấu hiệu prompt injection / bí mật (tính khi đọc, chỉ để người duyệt thấy)
