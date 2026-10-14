# ADR 0006 — Tách người tạo yêu cầu và người duyệt

- Ngày: 2026-10-15 • Trạng thái: chấp nhận • Thay thế một phần [ADR 0004](0004-mot-vai-tro-de.md)

## Bối cảnh

ADR 0004 (2026-10-08) cho Reviewer được duyệt cả yêu cầu do chính mình tạo, vì demo đề bài chỉ có hai vai trò. CLAUDE.md bản 2
(mục 3.2) yêu cầu bật mặc định việc tách người tạo và người duyệt (`REQUIRE_SEPARATE_REVIEWER=true`). Hai quyết định mâu thuẫn
nên đã hỏi lại người dùng; người dùng chọn bật lại (2026-10-15).

## Quyết định

- Thêm công tắc `REQUIRE_SEPARATE_REVIEWER`, mặc định `true`.
- Luật nằm ở `review_permission_error(role, reviewer, requester)` trong `src/agents/runner.py` (CLI và API dùng chung): Reviewer
  trùng tên người tạo yêu cầu thì bị chặn với thông báo "Người tạo yêu cầu không được tự duyệt hoặc từ chối".
- Vai trò vẫn là ba vai trò của ADR 0004 (engineer / reviewer / admin; chỉ Reviewer duyệt). Tắt công tắc khi chạy demo cá nhân
  bằng một tài khoản duy nhất.

## Hệ quả

- Một người muốn thử cả hai phía cần hai tài khoản (Engineer + Reviewer) **và** tên khác nhau; hai vai trò khác nhau của cùng một
  tên không tồn tại vì mỗi tài khoản có đúng một vai trò, nên luật này chủ yếu chặn đường CLI (tên do người vận hành khai) và
  tài khoản bị đổi vai trò sau khi tạo yêu cầu.
- Test cũ "Reviewer được duyệt yêu cầu của chính mình" đổi thành "bị chặn mặc định, được phép khi tắt công tắc".
