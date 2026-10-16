---
paths:
  - "src/api/**/*.py"
---

# Quy tắc cho API

- Thao tác làm agent chạy tiếp trả `202` ngay, chạy nền, xếp hàng lần lượt.
- Lỗi trả `detail` bằng tiếng Việt, không lộ traceback.
- Người dùng lấy từ header `X-User`; `X-Role` chỉ dùng khi bật `REQUIRE_SEPARATE_REVIEWER`.
- Endpoint mới: cập nhật bảng API trong `README.md` và thêm test trong `tests/test_api.py`.
