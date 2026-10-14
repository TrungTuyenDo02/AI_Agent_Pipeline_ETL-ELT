"""Hợp đồng dữ liệu bàn giao giữa các node/agent (CLAUDE.md mục 3 và 13): một khuôn Pydantic cố định cho mỗi lần bàn giao.

Giống phiếu bàn giao có mẫu sẵn: node sinh ra dữ liệu PHẢI đi qua khuôn trước khi ghi vào state, nên sai tên trường, sai kiểu
hay thêm trường lạ sẽ báo lỗi ngay ở node gây ra, không đợi tới node nhận mới vỡ. Khuôn **giữ nguyên hình dạng dict đang
lưu trong state/checkpoint** (không đổi định dạng, lần chạy cũ vẫn đọc được).

Đã có khuôn từ trước (không lặp lại ở đây): `PipelineSpec` (spec.py), `Evidence`, `OptimizationReport`, `ReviewDecision`
(evidence.py), đầu ra LLM của 4 agent (llm_outputs.py).
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SafetyResult(_Contract):
    """V1 → Codegen/Sandbox: kết quả kiểm tra an toàn."""

    passed: bool
    issues: list[str] = Field(default_factory=list)


class SandboxResult(_Contract):
    """V2 → Codegen/Optimizer/Review: kết quả `dbt build` trong sandbox."""

    passed: bool
    error: str = ""
    target_rows: int | None = None
    sample: list[dict[str, str]] | None = None
    models_ok: int = 0
    models_total: int = 0
    tests_ok: int = 0
    tests_total: int = 0


class PlanDecision(_Contract):
    """J1b → Planner: Engineer đồng ý hoặc yêu cầu sửa kế hoạch (sửa bắt buộc có ghi chú)."""

    decision: Literal["approve", "revise"]
    note: str = ""
    options: dict[str, str] = Field(
        default_factory=dict
    )  # lựa chọn pipeline DE đã chọn (load_mode, schedule, incremental_column)


class OptCandidate(_Contract):
    """E4 → V3: một bản viết lại đang chờ kiểm chứng (đã gồm phép đo baseline của lần đầu)."""

    original_sql: str
    sql: str = ""
    before: dict[str, Any]
    findings: list[dict[str, str]] = Field(default_factory=list)
    source: Literal["rules", "sqlglot", "llm"]
    explanation: str = ""
    warehouse_hints: list[str] = Field(default_factory=list)
    assumptions: list[Any] = Field(default_factory=list)
    applied: list[str] = Field(default_factory=list)
    invalid: str = ""
    tried: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)
    attempt: int = 1
    llm_cost_usd: float = 0.0
    bench: str | None = None
    feedback: str | None = None


def hand_off(contract: type[BaseModel], data: dict) -> dict:
    """Kiểm `data` theo khuôn rồi trả lại dict (JSON thuần, đúng các khóa đã đưa vào) để ghi vào state. Sai khuôn → ValidationError nêu rõ trường."""
    return contract.model_validate(data).model_dump(mode="json", exclude_unset=True)
