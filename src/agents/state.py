"""State của LangGraph (TypedDict, total=False). Hợp đồng chi tiết ở `src/models/` lưu dưới dạng dict."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class PipelineState(TypedDict, total=False):
    """Bộ nhớ chung giữa các node. Mỗi node chỉ trả về các trường nó thay đổi."""

    # Đầu vào
    run_id: str  # id lần chạy (trùng thread_id của checkpointer)
    request_text: str  # yêu cầu bằng ngôn ngữ thường
    requester: str  # người tạo yêu cầu (không được tự duyệt)

    # G0 Cửa kiểm tra đầu vào
    input_gate: dict  # GateResult.model_dump(): status, tier, code, message, examples, missing
    clarify_rounds: int  # số vòng hỏi làm rõ đã dùng (J1); trần MAX_CLARIFY_ROUNDS

    # E1 Planner ⇄ J1, V0
    source_catalog: list[
        dict
    ]  # nguồn phát hiện được: schema thật, `stats` do code đếm (+ mẫu đã che PII cho giao diện)
    answers: dict[str, str]  # câu trả lời làm rõ (J1): id câu hỏi → lựa chọn
    answered: list[dict]  # lịch sử J1 kèm nội dung câu hỏi: {id, question, answer} (để Planner hiểu ngữ cảnh)
    spec: dict  # PipelineSpec.model_dump()
    spec_errors: list[str]  # lỗi V0 (rỗng = đạt)
    plan_rounds: int  # số lần Planner đã chạy
    plan_review: dict  # quyết định J1b gần nhất: {"decision": "approve"|"revise", "note": "..."}
    plan_feedback: list[str]  # ghi chú DE yêu cầu sửa kế hoạch (Planner đọc khi lập lại)
    plan_reviews: int  # số lần DE yêu cầu sửa kế hoạch

    # E0, P, E2
    workspace: str  # đường dẫn workspace dbt
    row_counts: dict[str, int]  # số dòng mỗi bảng raw sau khi nạp
    profile: dict  # hồ sơ dữ liệu từng bảng raw
    datasets: dict[str, str]  # tên bộ dữ liệu thử → đường dẫn file DuckDB
    schema_snapshot: dict  # Vs: ảnh chụp cấu trúc nguồn (cột → kiểu, giá trị cột phân loại); thành chuẩn khi duyệt
    schema_report: dict  # Vs: SchemaReport so với bản đã duyệt (thêm/xóa/đổi kiểu/giá trị mới + đề xuất)
    schema_decision: dict  # Vs: Engineer xác nhận khi có cột bị xóa/đổi tên: {by, renames}

    # E3, E3b, V1, V2
    code_files: dict[str, str]  # file do Codegen sinh: đường dẫn tương đối → nội dung
    code_notes: list[str]  # giải thích của Codegen (claimed)
    test_files: dict[str, str]  # file test do code + Testgen sinh
    test_notes: list[str]  # giải thích của Testgen (claimed)
    previous_files: dict[str, str]  # bộ file của vòng duyệt trước (để xem diff)
    safety: dict  # kết quả V1: {"passed": bool, "issues": [...]}
    reconciliation: list[dict]  # V2: số dòng raw → staging từng nguồn (mục 9: không loại dòng im lặng)
    value_filters: list[dict]  # package: điều kiện lọc/phân nhóm cứng theo giá trị (tô sáng cho Reviewer)
    sandbox: dict  # kết quả V2: {"passed", "error", "signature", "results", "sample", ...}
    fix_attempts: int  # số lần sửa sau lỗi V1/V2 trong vòng hiện tại
    error_signatures: list[str]  # chữ ký lỗi đã gặp (phát hiện lỗi lặp)
    error_notes: list[str]  # mô tả lỗi đã che số liệu (ghi vào bộ nhớ agent khi lần chạy sửa xong)
    rescue_hint: str  # gợi ý của con người ở bước cứu hộ
    rescue_count: int  # số lần cứu hộ

    # E4, V3
    optimization: dict  # OptimizationReport.model_dump(); rỗng = chưa tối ưu
    opt_attempts: int  # số lần đề xuất viết lại
    opt_candidate: dict  # đề xuất hiện tại của E4 chờ V3 kiểm tra

    # J2
    evidence: dict  # Evidence.model_dump(): measured tách claimed
    review: dict  # ReviewDecision.model_dump() gần nhất
    review_notes: list[str]  # ghi chú từ chối của Reviewer
    review_rounds: int  # số lần bị từ chối

    # Chung
    llm_usage: Annotated[list[dict], operator.add]  # mỗi lần gọi LLM thêm một mục (token, chi phí)
    status: str  # RunStatus hiện tại
    error: str  # lỗi dừng hẳn (FAILED)
