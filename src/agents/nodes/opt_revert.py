"""V Khôi phục bản gốc (code thuần, 0 token): bản tối ưu vừa áp dụng không qua V1/V2 kiểm lại hoặc lệch kết quả trên sandbox.

Bản gốc đã qua V1+V2 trước khi tối ưu, nên không nhờ Codegen sửa bản tối ưu (tốn token, có thể làm đổi kết quả): trả lại code
gốc, ghi `skipped` kèm lý do, rồi chạy lại V1+V2 để sandbox, kết quả mẫu và bằng chứng khớp với code gốc.
"""

from src.agents.nodes.codegen import last_error
from src.agents.state import PipelineState
from src.agents.tools.scrub import scrub_error
from src.models.evidence import DatasetCheck

DETAIL_CHARS = 300


def opt_revert_node(state: PipelineState) -> dict:
    """Trả `code_files` về bản trước tối ưu và đổi quyết định tối ưu thành `skipped`."""
    baseline = state.get("opt_baseline") or {}
    report = state.get("optimization") or {}
    error = scrub_error(last_error(state)).strip().splitlines()
    detail = f"Bản tối ưu không qua kiểm tra lại V1/V2: {error[0][:DETAIL_CHARS] if error else 'không rõ lỗi'}"
    check = DatasetCheck(dataset="sandbox", equal=False, detail=detail).model_dump(mode="json")
    return {
        "code_files": baseline.get("code_files") or state.get("code_files", {}),
        "optimization": {
            **report,
            "decision": "skipped",
            "reason": f"{detail}. Đã khôi phục bản gốc (đã qua V1+V2), không nhờ Codegen sửa bản tối ưu.",
            "equivalence": [*report.get("equivalence", []), check],
        },
        "opt_baseline": {},
    }
