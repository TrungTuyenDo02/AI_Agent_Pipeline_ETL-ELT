# HANDOFF — chuyển sang Claude Code Cloud (2026-10-18)

## Việc đang làm

- Nhánh bàn giao: `wip/cloud-pause-resume-2026-10-18`, tách từ `feat/guest-mode` tại `aa6822f`.
- Đây là snapshot WIP: có cả Đợt A (giao diện) và Đợt B (pause/resume chưa hoàn tất). Không coi commit bàn giao là bản đã qua CI.
- Đọc [hướng dẫn cloud](docs/CLOUD_HANDOFF.md) trước khi sửa. [Prompt tiếp tục](docs/CLAUDE_CLOUD_PROMPT.md) đã chuẩn bị để người dùng dán vào phiên mới.
- Phiên chuẩn bị bàn giao chỉ cập nhật tài liệu và đóng gói trạng thái có sẵn; không sửa logic, không chạy lại pytest/frontend và không chạy migration.
- `.venv` local hiện không khởi động được vì Python 3.11 mà nó trỏ tới không còn ở đường dẫn cũ. Cloud cần tạo môi trường mới từ requirements; không chuyển virtualenv local.

## Đợt A — theo báo cáo phiên Claude trước

- Thanh trên hai hàng và `PrimaryNav.tsx`; mục dư vào menu Thêm, thanh dưới điện thoại tối đa 5 ô. Bỏ Dock và RunSearch/Ctrl+K.
- Viết lại `/docs`, thêm `DocsSectionNav.tsx` và 4 ảnh demo sáng/tối trong `frontend/public/docs/`; sửa câu chữ, CSS, màu tương phản và tài liệu frontend.
- Phiên trước báo lint, typecheck, format:check, check:contrast, build đạt; đã kiểm tra nhiều chiều rộng, vai trò và sáng/tối; `/docs` 40/40 kiểm tra đạt. Chưa chạy lại trong phiên bàn giao này.
- Ảnh trước/sau ở `scratchpad/ui/shots/` theo báo cáo cũ không được xác nhận có trên cloud. Bốn ảnh trong `frontend/public/docs/` là asset cần bàn giao.

## Đợt B — code đã có, cần hoàn thiện và kiểm chứng

- Migration `0010_run_controls.py`, cờ pause trong store; runner chạy từng node và tiếp tục từ checkpoint; khóa chống chạy trùng trong jobs.
- `RunBusyError` → HTTP 409 trong `src/main.py`; API pause/resume và audit trong `src/api/runs.py` đã có.
- Nhãn CLI, stages, kiểu/trạng thái/bộ lọc/nhật ký frontend và `PauseControl.tsx` đã có.
- Hợp đồng hiện có thêm `RunStatus.PAUSED` và `RunRecord.pause_requested=False`. Việc đóng gói WIP không xác nhận thiết kế đã được duyệt; giữ tương thích checkpoint/API cũ và không mở rộng thêm hợp đồng ngoài phạm vi này.
- Test đã có ở `tests/test_api/test_pause_api.py`. Chưa thấy ADR 0016 dù code đang dẫn chiếu số này.

## Kết quả mới nhất từ log người dùng cung cấp

- Pause/resume: **10 passed, 2 failed** trong 78.07 giây. Hai test lỗi:
  - `test_pause_while_node_runs_finishes_node_then_stops_before_next`: kỳ vọng `clarify`, thực tế node tiếp theo là `spec_check`.
  - `test_resume_refused_when_budget_or_limits_hit`: kỳ vọng 409 do `RUN_TOKEN_BUDGET`, thực tế 202.
- Cần tái hiện và xác định lỗi test hay logic; chưa đủ bằng chứng kết luận chỉ sai giả định test.
- Bộ test cũ chỉ có output tới khoảng 43%; phiên trước báo hết thời gian 900 giây. Exit code của lệnh bọc không chứng minh pytest đã hoàn tất.
- Số 1149 passed/20 skipped/2 xfailed/91.85% ở bàn giao trước là baseline lịch sử, không áp dụng cho snapshot pause/resume hiện tại.

## Thứ tự tiếp tục

1. Thiết lập môi trường mock/SQLite kiểm thử theo hướng dẫn cloud; chạy lại file test pause/resume và sửa nguyên nhân.
2. Kiểm chứng ranh giới node, resume không chạy lại phần đã xong, queue/concurrency, restart, quyền, giới hạn/ngân sách và audit.
3. Kiểm tra migration, checkpoint/API cũ và UI cho Engineer/người khác/khách.
4. Viết ADR 0016, cập nhật WORKLOG, README, RUNBOOK và API.md cho endpoint mới.
5. Chạy `python scripts/tasks.py ci` và `python scripts/tasks.py frontend-check` đến khi có kết quả cuối. Ghi đúng phần chưa kiểm chứng.
- Receipt từng run và phân giải source_id khi trùng tên bảng vẫn là backlog sau đợt này.
- Backend mock ở cổng 8000 được phiên trước báo đang chạy trên máy local; chưa kiểm tra/tắt trong phiên bàn giao. Cloud là môi trường riêng.

## Baseline trước đợt giao diện/pause-resume

## Đã xong
- Extract: lọc file/bảng SQLite theo allowed_tables trước đọc dữ liệu; cache phân biệt phạm vi quyền.
- Dataset eval/datasets/extract_v1 có nguồn/oracle đóng băng riêng, 21 ca, receipt source_id/file/hash/schema/digest.
- eval-extract chạy độc lập; run_eval tích hợp điểm Extract và truyền lỗi tiến trình con.
- Sửa `.claude/rules/api.md`: cookie phiên, vai trò từ backend, CSRF; cập nhật đường dẫn test.
- So bảng vá theo tên/thứ tự/kiểu cột và số lần xuất hiện từng dòng; hỗ trợ dữ liệu lồng nhau và NaN.
- Giữ các trường regression cũ; thêm schema_same và ghi rõ đổi cấu trúc trên bằng chứng/tiến trình.
- Bỏ khối lặp trong frontend/CLAUDE.md cục bộ; CLAUDE.md tiếp tục bị Git bỏ qua theo ý người dùng.
- README, report, RUNBOOK, WORKLOG đã đồng bộ với bản sửa và kết quả CI.

## Trạng thái kiểm chứng lịch sử (không phải snapshot WIP hiện tại)
- `python scripts/tasks.py ci`: 1149 passed, 20 skipped, 2 xfailed, độ phủ 91.85%; không có failure.
- Frontend: lint, format:check, typecheck, check:contrast, build đều qua.
- Docker chưa kiểm tra vì máy không có lệnh docker.

## Backlog ở bàn giao trước (đã được ưu tiên lại ở trên)
1. Tiếp theo: receipt cho từng run và phân giải source_id khi trùng tên bảng; eval hiện chọn nguồn tường minh.
2. Bàn giao trước còn yêu cầu xem diff và commit. Phiên hiện tại đóng gói thành snapshot WIP theo yêu cầu người dùng.
3. Có thể kiểm tra Docker bằng CI GitHub sau khi push.

## Quyết định cần nhớ
- Giữ nguyên tên node và hợp đồng Pydantic; checkpoint cũ chưa có schema_same vẫn đọc được.
- Chỉ số pytest được cập nhật từ CI; chưa chạy lại phép đo LLM thật hoặc golden/mutation trong phiên này.

- Extract eval 21/21 (tổng hợp, không mạng/LLM); chưa chấm PostgreSQL thật, native phức tạp/múi giờ hay CDC.
