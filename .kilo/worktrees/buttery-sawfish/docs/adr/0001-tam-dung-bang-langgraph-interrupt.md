# ADR 0001 — Tạm dừng ở J1/J2/cứu hộ bằng LangGraph interrupt + checkpointer SQLite

- Ngày: 2026-10-02 • Trạng thái: Chấp nhận

## Bối cảnh
Luồng phải dừng chờ con người (J1 làm rõ, J2 duyệt, cứu hộ) rồi chạy tiếp, từ CLI lẫn API, kể cả khi
lệnh `review` chạy ở một tiến trình khác lệnh `run`.

## Quyết định
Dùng `langgraph.types.interrupt()` trong node `clarify`, `review`, `rescue` và `SqliteSaver`
(`langgraph-checkpoint-sqlite`) lưu state vào `data/checkpoints.db`; `thread_id` = `run_id`.
Tiếp tục bằng `Command(resume=...)`. Đã chạy thử với langgraph 1.2.12 trước khi dùng.

## Hệ quả
- Một graph duy nhất, khớp sơ đồ; CLI và API dùng chung `src/agents/runner.py`.
- Thêm 1 dependency nhỏ (`langgraph-checkpoint-sqlite`).
- Node có `interrupt()` chạy lại từ đầu khi tiếp tục → các node này không làm việc có tác dụng phụ trước `interrupt()`.
- Kiểm tra quyền (vai trò reviewer, không tự duyệt) làm ở runner trước khi resume và kiểm lại trong node.
