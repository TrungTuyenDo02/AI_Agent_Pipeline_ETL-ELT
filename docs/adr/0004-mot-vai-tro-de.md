# ADR 0004 — Vai trò và luật duyệt

- Ngày: 2026-10-02 • Sửa: 2026-10-08 • Trạng thái: chấp nhận (bản sửa thay quyết định "một vai trò DE")

## Bối cảnh

Bản đầu chọn một vai trò DE tự duyệt, có công tắc `REQUIRE_SEPARATE_REVIEWER`. Ngày 2026-10-08, CLAUDE.md bổ sung yêu
cầu đăng nhập và phân quyền Engineer/Reviewer kiểm ở backend ("chỉ code đã được Reviewer duyệt mới được merge, không
có đường tắt"). Hai quyết định mâu thuẫn nên đã hỏi lại người dùng.

## Quyết định (người dùng chọn)

- Đăng nhập bằng tài khoản nội bộ do doanh nghiệp cấp; mật khẩu băm argon2id; phiên phía máy chủ (cookie HttpOnly).
- Ba vai trò: **engineer** (tạo yêu cầu, J1, J1b, cứu hộ), **reviewer** (J2 duyệt/từ chối, duyệt sổ lỗi),
  **admin** (quản lý tài khoản, không duyệt code).
- **Chỉ Reviewer được duyệt**; Reviewer **được** duyệt cả yêu cầu do mình tạo (không chọn đề xuất cấm tự duyệt).
- Bỏ vai trò `de` và công tắc `REQUIRE_SEPARATE_REVIEWER`.
- Luật nằm ở `review_permission_error()` trong `src/agents/runner.py` (CLI và API dùng chung); API kiểm thêm bằng
  `require_role` ở `src/api/deps.py`.

## Hệ quả

- Demo đúng đề 2 vai trò; một người muốn vừa tạo vừa duyệt thì cần hai tài khoản (Engineer + Reviewer).
- Muốn cấm tự duyệt sau này: thêm điều kiện so `reviewer` với `requester` trong `review_permission_error()` + test.
