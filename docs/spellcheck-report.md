# Báo cáo kiểm chính tả và viết hoa (Brief bước 3)

Ngày: 2026-10-18. Công cụ: `npm run lint:text` (`frontend/scripts/lint-text.mjs`, tự viết, không thêm thư viện; dùng trình phân tích của `typescript` có sẵn).

## Quy tắc

- **Viết hoa đầu câu, đầu tiêu đề, đầu nhãn.** Giữ nguyên tên riêng viết thường: dbt, sqlglot, tên định danh trong code.
- **Một ý một từ:** luôn "duyệt", không "phê duyệt" hay "approve" trong câu tiếng Việt.
- **Khoảng trắng:** không hai dấu cách liền nhau, không dấu cách trước dấu câu.

Phạm vi quét: `content/`, `lib/`, `app/`, `components/` (chú thích không tính). Bỏ qua `lib/demo/` vì là dữ liệu mẫu giả lập lời agent, log, SQL.
Chỉ bắt lỗi viết thường ở vị trí chắc chắn là đầu câu: chữ trong `content/` và `lib/*Text.ts`, thuộc tính `title`/`aria-label`/`placeholder`/`alt`/`label`, chữ đứng đầu một thẻ JSX, thông báo `toast()`/`setError()`/`new Error()`.
Mảnh câu nối tiếp (chữ trong `<strong>` giữa câu, chú thích mở đầu bằng "(" hoặc "·") không bị tính.

## Chuỗi đã sửa (trước → sau)

| File | Loại | Trước | Sau |
|---|---|---|---|
| `frontend/lib/guideText.ts` | Câu ví dụ điền sẵn | gộp đơn hàng 3 nguồn, tính doanh thu ngày | Gộp đơn hàng 3 nguồn, tính doanh thu ngày |
| `frontend/app/sources/page.tsx` | Nhãn | tham chiếu: {source.secret_ref} | Tham chiếu: {source.secret_ref} |
| `frontend/components/catalog/DataProfile.tsx` | Nhãn (badge) | khóa | Khóa |
| `frontend/components/catalog/DataProfile.tsx` | Nhãn (chip) | cả bảng | Cả bảng |
| `frontend/components/ErrorBook.tsx` | Nhãn (badge) | gặp {entry.occurrences} lần | Gặp {entry.occurrences} lần |
| `frontend/components/GuestBar.tsx` | Nhãn (badge) | số liệu mẫu | Số liệu mẫu |
| `frontend/components/home/Dashboard.tsx` | Tiêu đề phụ | chỉ ghi thêm, mới nhất trước | Chỉ ghi thêm, mới nhất trước |
| `frontend/components/run/EvidencePanel.tsx` | Nhãn (badge) | đã đo bằng code, 0 token | Đã đo bằng code, 0 token |
| `frontend/components/run/EvidencePanel.tsx` | Nhãn (badge) | chưa kiểm chứng | Chưa kiểm chứng |
| `frontend/components/run/OptimizationScreen.tsx` | Chú thích ô bảng | tỉ lệ theo thời gian chạy | Tỉ lệ theo thời gian chạy |
| `frontend/components/run/OptimizationScreen.tsx` | Ô bảng | bản gốc | Bản gốc |
| `frontend/components/run/OptimizationScreen.tsx` | Nhãn (badge) | chưa kiểm chứng | Chưa kiểm chứng |
| `frontend/components/run/PlanReview.tsx` | Lựa chọn mặc định | — chọn cột — | — Chọn cột — |
| `frontend/components/run/ReviewScreen.tsx` | Nhãn (badge) | không có cảnh báo | Không có cảnh báo |
| `frontend/components/run/ReviewScreen.tsx` | Nhãn (badge) | đổi | Đổi |
| `frontend/components/run/RunHeader.tsx` | Nhãn (badge) | chờ bạn | Chờ bạn |
| `frontend/components/run/RunHeader.tsx` | Nhãn (badge) | đang xếp hàng: còn {detail.queue_position} lần chạy phía trước | Đang xếp hàng: còn {detail.queue_position} lần chạy phía trước |
| `frontend/components/run/RunHeader.tsx` | Nhãn (badge) | agent đang chạy… | Agent đang chạy… |
| `frontend/components/run/studio/LiveNode.tsx` | Nhãn | đang làm | Đang làm |

## Cố ý giữ viết thường

| Chuỗi | Lý do |
|---|---|
| 4 nhãn số liệu ở trang đăng nhập ("lỗi cố ý bị bộ kiểm chứng bắt"…) | Đứng ngay sau con số lớn ("93% lỗi cố ý…"), đọc liền một câu |

## Kiểm khác

- Thuật ngữ: không còn "phê duyệt"; "approve" chỉ còn trong chữ tiếng Anh (trang đăng nhập EN) và tên biến.
- Dấu tiếng Việt: không phát hiện từ sai dấu trong các chuỗi đã quét (kiểm bằng mắt khi rà 28 chỗ bị bắt ở lần quét đầu).
- Chữ trang giới thiệu (/docs) được gom vào `frontend/content/landing.ts` và viết lại ngắn hơn ở bước 1 (mỗi đoạn tối đa 2 dòng).

Kết quả hiện tại: `npm run lint:text` → "Chữ giao diện sạch."
