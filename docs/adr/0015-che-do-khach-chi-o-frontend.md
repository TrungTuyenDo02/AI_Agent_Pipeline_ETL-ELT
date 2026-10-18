# ADR 0015 — Chế độ khách chạy bằng dữ liệu mẫu, chỉ ở frontend

- Ngày: 2026-10-17 • Trạng thái: chấp nhận • Không đổi backend, hợp đồng `src/models/` hay tên node

## Vấn đề

Người xem (giám khảo, đồng nghiệp) cần thử trọn luồng Engineer → Reviewer mà không có tài khoản, không tốn token và không chạm dữ
liệu hay máy chủ thật. Tạo tài khoản khách ở backend sẽ phải nới phân quyền, hạn mức chi phí và nhật ký kiểm toán.

## Quyết định

- Chế độ khách nằm hoàn toàn ở web. Vào bằng nút "Dùng thử với dữ liệu mẫu" ở màn đăng nhập hoặc liên kết `/demo`. Cờ và vai
  (Engineer/Reviewer, không có Admin) lưu ở `sessionStorage`.
- Khi là khách, `rawRequest` (`frontend/lib/api.ts`) chuyển mọi lời gọi `/api/v1/...` sang `lib/demo/router.ts` (nạp bằng `import()`
  động). Router trả lời từ dữ liệu mẫu, chép luật vai trò, bước chờ và câu báo lỗi của backend. Thêm một lưới chặn `fetch` tới
  backend (`lib/guest.ts`) báo lỗi rõ trong console.
- Dữ liệu mẫu `lib/demo/fixtures.ts` do `scripts/demo_fixtures.py` sinh. Script chạy luồng API thật với `LLM_PROVIDER=mock` trong thư
  mục tạm, rồi làm sạch: bỏ đường dẫn máy, đổi tên kênh bán thành tên chung. Token, chi phí và thời gian LLM điền số liệu mẫu; web luôn
  ghi chú "số liệu mẫu". File khai báo `satisfies DemoFixtures` nên API đổi khuôn mà chưa sinh lại thì `tsc` báo lỗi.
- Tiến trình "đang chạy" tính theo đồng hồ từ các khung chụp thật, không dùng hẹn giờ. Thao tác ghi đổi trạng thái trong
  `sessionStorage`; nút "Làm lại từ đầu" xóa sạch.
- Thuộc J-E-V: đây là phần trình diễn, không thêm bước J/E/V nào. Kiểm chứng bằng code thuần (V):
  `tests/test_demo_fixtures.py` quét dữ liệu mẫu đã commit.

## Hệ quả

- Không có lệnh gọi mạng nào tới backend khi là khách (đã đo bằng trình duyệt headless: 0 request). Web deploy một mình vẫn dùng thử
  được.
- Dữ liệu mẫu có thể lệch hành vi mới của backend: đổi API thì chạy lại `python scripts/demo_fixtures.py`.
- Khách không tải được gói zip và không sửa được sổ nguồn, từ điển, người dùng (báo "Chế độ khách không lưu thay đổi này").
