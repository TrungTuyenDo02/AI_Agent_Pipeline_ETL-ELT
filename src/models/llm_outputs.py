"""Schema đầu ra của từng node LLM (structured output, chuẩn prompt U1 quy tắc 2.2-4).

Gửi kèm lời gọi API thay cho đoạn "hãy trả về JSON như sau…" trong prompt. Mọi trường bắt buộc, không thêm trường
lạ (đúng luật `strict` của OpenAI). Node vẫn tự kiểm tra lại đầu ra: schema chỉ giảm lỗi định dạng, không thay V.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutColumn(_Strict):
    name: str
    type: str = Field(description="DATE|BIGINT|DOUBLE|VARCHAR")
    description: str
    references: str = Field(description="foreign key to another model as model.column; empty if none")


class OutMetric(_Strict):
    name: str
    description: str


class OutQuestion(_Strict):
    id: str
    question: str
    options: list[str] = Field(description="2-4 short choices")
    column: str = Field(description="source.column for a which-values question, else empty")


class OutSignals(_Strict):
    restricted_pii: bool = Field(
        description="true only if the request says personal data must not enter the warehouse as-is"
    )
    small_subset_of_large: bool = Field(description="true only if the request needs a tiny part of a very large source")


class OutPlanStep(_Strict):
    title: str
    detail: str
    reason: str


class PlannerOutput(_Strict):
    sources: list[str] = Field(description="source names from the catalog")
    target: str
    grain: list[str]
    output_columns: list[OutColumn]
    metrics: list[OutMetric]
    filters: list[str]
    unknowns: list[str]
    assumptions: list[str]
    questions: list[OutQuestion]
    signals: OutSignals
    plan_summary: str
    plan: list[OutPlanStep]


class OutFile(_Strict):
    path: str
    content: str


class CodegenOutput(_Strict):
    files: list[OutFile]
    notes: list[str]


class TestgenOutput(_Strict):
    expected_sql: str
    notes: list[str]


class OptimizerOutput(_Strict):
    sql: str
    explanation: str
    warehouse_hints: list[str]


OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "planner": PlannerOutput,
    "codegen": CodegenOutput,
    "testgen": TestgenOutput,
    "optimizer": OptimizerOutput,
}


def _inline(node: Any, defs: dict[str, Any]) -> Any:
    """Thay `$ref` bằng định nghĩa, bỏ `title` (tốn token, không cần cho model)."""
    if isinstance(node, list):
        return [_inline(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _inline(defs[node["$ref"].rsplit("/", 1)[-1]], defs)
    out = {}
    for key, value in node.items():
        if key in ("title", "$defs"):
            continue
        if key == "properties":  # tên thuộc tính (có thể là "title") giữ nguyên
            out[key] = {name: _inline(prop, defs) for name, prop in value.items()}
        else:
            out[key] = _inline(value, defs)
    return out


def output_schema(task: str) -> dict | None:
    """JSON Schema phẳng (không `$ref`) cho tác vụ; None nếu tác vụ không có schema."""
    model = OUTPUT_MODELS.get(task)
    if model is None:
        return None
    schema = model.model_json_schema()
    return _inline(schema, schema.get("$defs", {}))
