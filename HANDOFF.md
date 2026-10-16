# HANDOFF

## Đã xong
- Extract: lọc file/bảng SQLite theo allowed_tables trước đọc dữ liệu; cache phân biệt phạm vi quyền.
- Dataset eval/datasets/extract_v1 có nguồn/oracle đóng băng riêng, 21 ca, receipt source_id/file/hash/schema/digest.
- eval-extract chạy độc lập; run_eval tích hợp điểm Extract và truyền lỗi tiến trình con.
- Sửa `.claude/rules/api.md`: cookie phiên, vai trò từ backend, CSRF; cập nhật đường dẫn test.
- So bảng vá theo tên/thứ tự/kiểu cột và số lần xuất hiện từng dòng; hỗ trợ dữ liệu lồng nhau và NaN.
- Giữ các trường regression cũ; thêm schema_same và ghi rõ đổi cấu trúc trên bằng chứng/tiến trình.
- Bỏ khối lặp trong frontend/CLAUDE.md cục bộ; CLAUDE.md tiếp tục bị Git bỏ qua theo ý người dùng.
- README, report, RUNBOOK, WORKLOG đã đồng bộ với bản sửa và kết quả CI.

## Trạng thái kiểm chứng
- `python scripts/tasks.py ci`: 1149 passed, 20 skipped, 2 xfailed, độ phủ 91.85%; không có failure.
- Frontend: lint, format:check, typecheck, check:contrast, build đều qua.
- Docker chưa kiểm tra vì máy không có lệnh docker.

## Việc tiếp theo
1. Tiếp theo: receipt cho từng run và phân giải source_id khi trùng tên bảng; eval hiện chọn nguồn tường minh.
2. Xem diff và commit các thay đổi đã sửa; chưa commit/push trong phiên này.
3. Có thể kiểm tra Docker bằng CI GitHub sau khi push.

## Quyết định cần nhớ
- Giữ nguyên tên node và hợp đồng Pydantic; checkpoint cũ chưa có schema_same vẫn đọc được.
- Chỉ số pytest được cập nhật từ CI; chưa chạy lại phép đo LLM thật hoặc golden/mutation trong phiên này.

- Extract eval 21/21 (tổng hợp, không mạng/LLM); chưa chấm PostgreSQL thật, native phức tạp/múi giờ hay CDC.
