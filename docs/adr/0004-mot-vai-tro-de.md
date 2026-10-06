# ADR 0004 — Một vai trò DE, bước duyệt giữ nguyên

- Ngày: 2026-10-02 • Trạng thái: chấp nhận

## Bối cảnh

Đề bài nêu 2 vai trò (Engineer / Reviewer) và người tạo yêu cầu không tự duyệt. Người dùng chính của sản phẩm là Data
Engineer (DE): thường một người vừa mô tả yêu cầu vừa kiểm tra code sinh ra.

## Quyết định

- Mặc định chỉ một vai trò **DE**; người tạo yêu cầu được tự duyệt.
- **Bước duyệt J2 giữ nguyên**: vẫn dừng ở bản duyệt, hiện diff, bằng chứng "Code đo | LLM nói", báo cáo tối ưu.
  Agent không tự merge.
- Công tắc `REQUIRE_SEPARATE_REVIEWER=true` bật lại luật 2 người (chỉ `reviewer` duyệt, khác người tạo) để demo
  đúng mô tả đề bài khi cần.
- Luật nằm ở một chỗ: `review_permission_error()` trong `src/agents/runner.py` (CLI và API dùng chung).

## Hệ quả

- Đơn giản cho DE dùng một mình; vẫn giữ HITL (con người quyết định trước khi merge).
- Rủi ro: BTC chấm theo đề có 2 vai trò → khi demo nên trình bày công tắc này.
