"""J1 Hỏi làm rõ: graph tạm dừng, chờ con người chọn đáp án cho từng câu hỏi trắc nghiệm."""

from langgraph.types import interrupt

from src.agents.state import PipelineState
from src.models.spec import ClarifyQuestion


def value_answer(question: ClarifyQuestion, values: list[str]) -> str:
    """Câu trả lời dạng điều kiện rõ ràng cho Codegen, vd `shopee_orders: "status" IN ('COMPLETED')`."""
    source, _, column = question.column.partition(".")
    quoted = '"' + column.replace('"', '""') + '"'
    target = f"upper(trim({quoted}))" if question.normalized else quoted
    picked = ", ".join("'" + v.replace("'", "''") + "'" for v in values)
    return f"{source}: {target} IN ({picked})"


def _answer(question: ClarifyQuestion, value: object) -> str | None:
    """Câu thường: đúng nguyên văn một lựa chọn. Câu chọn nhiều: một hoặc nhiều lựa chọn, tất cả phải có sẵn."""
    if not question.multiple:
        return value if isinstance(value, str) and value in question.options else None
    picked = [value] if isinstance(value, str) else value if isinstance(value, list) else []
    if not picked or any(not isinstance(v, str) or v not in question.options for v in picked):
        return None
    return value_answer(question, [v for v in question.options if v in picked])  # giữ thứ tự lựa chọn, bỏ trùng


def valid_answers(questions: list[ClarifyQuestion], reply: object) -> dict[str, str]:
    """Chỉ giữ câu trả lời đúng id câu hỏi và nằm trong danh sách lựa chọn."""
    answers = reply.get("answers", {}) if isinstance(reply, dict) else {}
    by_id = {q.id: q for q in questions}
    chosen = {qid: _answer(by_id[qid], value) for qid, value in answers.items() if qid in by_id}
    return {qid: text for qid, text in chosen.items() if text is not None}


def clarify_node(state: PipelineState) -> dict:
    """Tạm dừng (interrupt) để hỏi; khi tiếp tục, gộp câu trả lời hợp lệ vào `answers`."""
    spec = state.get("spec", {})
    questions = [ClarifyQuestion.model_validate(q) for q in spec.get("questions", [])]
    reply = interrupt(
        {
            "kind": "clarify",
            "unknowns": spec.get("unknowns", []),
            "questions": [q.model_dump() for q in questions],
        }
    )
    chosen = valid_answers(questions, reply)
    answered = [{"id": q.id, "question": q.question, "answer": chosen[q.id]} for q in questions if q.id in chosen]
    return {
        "clarify_rounds": state.get("clarify_rounds", 0) + 1,
        "answers": {**state.get("answers", {}), **chosen},
        "answered": [*state.get("answered", []), *answered],
    }
