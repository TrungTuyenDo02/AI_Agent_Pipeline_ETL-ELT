---
paths:
  - "src/api/**/*.py"
---

# Quy tắc cho API

- Thao tác làm agent chạy tiếp trả `202` ngay, chạy nền, xếp hàng lần lượt.
- Lỗi trả `detail` bằng tiếng Việt, không lộ traceback.
- Người dùng và vai trò lấy từ phiên đăng nhập trong cookie `p113_session`, qua dependency ở `src/api/deps.py`; không tin `X-User` hoặc `X-Role` do client gửi.
- Thao tác ghi cần header `X-Requested-With` để kiểm tra CSRF; kiểm tra vai trò và quyền xem nguồn/lần chạy ở backend.
- Endpoint mới: cập nhật `docs/API.md` và thêm test trong `tests/test_api/`.
