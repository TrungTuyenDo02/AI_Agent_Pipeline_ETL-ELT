# Prompt để dán vào Claude Code Cloud

Chọn repository `TrungTuyenDo02/AI_Agent_Pipeline_ETL-ELT`, nhánh `wip/cloud-pause-resume-2026-10-18`. Sao chép phần bên trong khối dưới đây:

```text
Tiếp tục P-113: hoàn thiện Đợt B — tạm dừng/tiếp tục lần chạy.

Đầu tiên đọc HANDOFF.md và docs/CLOUD_HANDOFF.md. Các quy tắc cần
thiết từ CLAUDE.md cục bộ đã được đưa vào hướng dẫn cloud vì các
file CLAUDE.md đang bị Git bỏ qua theo lựa chọn của chủ dự án.

Nhánh bàn giao là snapshot WIP. Đợt A giao diện đã được phiên trước
báo kiểm tra đạt; giữ nguyên và chỉ sửa khi có hồi quy liên quan.
Không triển khai lại các phần Đợt B đã có; kiểm tra code trước.

Trạng thái test gần nhất trong log bàn giao: test_pause_api.py có
10 passed, 2 failed. Bộ test cũ chỉ có output tới khoảng 43%, chưa
hoàn tất. Số 1149 passed trong baseline cũ không áp dụng cho WIP này.

Hai lỗi cần tái hiện:
- test_pause_while_node_runs_finishes_node_then_stops_before_next:
  kỳ vọng clarify, thực tế node tiếp theo là spec_check.
- test_resume_refused_when_budget_or_limits_hit: kỳ vọng 409 vì
  RUN_TOKEN_BUDGET, thực tế 202.
Xác định lỗi test hay implementation; không đổi kỳ vọng chỉ để qua.

Thiết lập môi trường theo docs/CLOUD_HANDOFF.md: Python 3.11,
Node 22, dependencies đã ghim, mock và SQLite kiểm thử. Không cần
khóa API, .env hay tài khoản từ máy local. Nếu thiếu dependency,
cài từ requirements.txt và frontend/package-lock.json hiện có.

Viết kế hoạch ngắn trước khi sửa. Hoàn thiện và kiểm chứng:
dừng sau node đang chạy, dừng khi xếp hàng, resume không chạy lại
node đã xong, bấm lặp/đồng thời, restart, trạng thái chờ người/xong/lỗi,
quyền Engineer tạo run, CSRF, hạn mức/ngân sách và audit.
Kiểm tra migration 0010, tương thích checkpoint/API cũ và UI sáng/tối,
laptop/điện thoại; ẩn nút với khách và người không đủ quyền.

Giữ phạm vi bổ sung PAUSED/pause_requested đang có; báo rõ thay đổi
hợp đồng và kiểm chứng tương thích để tôi review, không tự mở rộng.
Không đổi tên node hoặc nới hàng rào kiểm chứng.

Viết ADR 0016; cập nhật WORKLOG, README, RUNBOOK, docs/API.md và
HANDOFF. Sau sửa, chạy đến kết quả cuối:
python scripts/tasks.py ci
python scripts/tasks.py frontend-check

Không gọi LLM thật, dùng dữ liệu thật, sửa production, deploy hoặc
tự merge. Không xóa/skip test hay hạ ngưỡng để kiểm tra qua.
Kết thúc bằng commit/diff để review và báo cáo tiếng Việt: đã đổi gì,
lệnh kiểm tra/kết quả cuối, phần chưa kiểm chứng và việc còn lại.
```
