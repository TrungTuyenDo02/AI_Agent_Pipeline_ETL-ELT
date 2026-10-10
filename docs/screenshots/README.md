# Ảnh chụp giao diện trước / sau khi bớt chật (2026-10-10)

Chụp ở chế độ mô phỏng (LLM `mock`), dữ liệu giả lập, bằng Chrome headless: 1440×900 (`-d`) và 390×844 (`-m`).
Ảnh trong `before/` và `after/`; ảnh dùng cho README nằm ở `web_*.png`.

**Cách đếm:** "khối" = thẻ/kính cấp ngoài cùng nhìn thấy trong khung 1440×900 chưa cuộn (đếm bằng script, có thể lệch ±1 với mắt người).
Chiều cao = `scrollHeight` của trang (px). Cột 4 là chiều cao trên điện thoại 390px.

| Màn | Khối nhìn thấy (trước → sau) | Cao 1440px (trước → sau) | Cao 390px (trước → sau) |
|---|---|---|---|
| home | 5 → 5 | 1240 → 994 | 2259 → 2012 |
| runs | 1 → 1 | 900 → 900 | 900 → 900 |
| run-clarify | 4 → 2 | 1453 → 1467 | 3250 → 2052 |
| run-plan | 5 → 3 | 2001 → 1825 | 4496 → 3298 |
| run-review-ready | 5 → 2 | 2561 → 1252 | 4615 → 1560 |
| review | 1 → 1 | 4932 → 2084 | 7602 → 3811 |
| optimize | 3 → 3 | 1723 → 1723 | 2641 → 2641 |
| run-catalog | 1 → 1 | 1746 → 1307 | 2698 → 2236 |
| catalog | 2 → 2 | 1842 → 1403 | 2828 → 2366 |
| errors | 0 → 0 | 900 → 900 | 900 → 900 |
| admin | 2 → 2 | 900 → 900 | 1383 → 1383 |

## Vấn đề thấy ở bản trước và cách sửa

| Màn | Vấn đề | Đã sửa |
|---|---|---|
| Tổng quan lần chạy | 3 thẻ bước đã xong (Yêu cầu, Làm rõ, Kế hoạch) chiếm chỗ; cột phải 3 khối kỹ thuật (token, sơ đồ, console); thẻ "Kết quả sandbox" lặp số liệu | Bước đã xong gộp một dòng thu gọn; chỉ mở bước hiện tại; token/chi phí/sơ đồ/console/kết quả mẫu vào ngăn "Chi tiết kỹ thuật" (đóng sẵn) |
| Duyệt code | Code đứng đầu, bằng chứng "Code đo \| LLM nói" nằm sau; trang dài ~4.900px | Bằng chứng lên đầu (danh sách cuộn trong khung), nút quyết định cạnh kiểm tra dữ liệu; code, tối ưu, chi phí đặt trong tab |
| Trang chủ (Engineer) | "Hoạt động của tôi" lặp đúng nội dung "Yêu cầu gần đây" | Bỏ khối trùng |
| Hồ sơ dữ liệu | Mặc định hiện mọi cột và 50 dòng xem trước | Mặc định chỉ cột có vấn đề (không có thì hiện hết); xem trước nằm trong "Xem trước…" đóng sẵn |

Chưa đổi (đã đạt ≤ 5 khối): Lần chạy, Tối ưu, Cấu trúc dữ liệu, Sổ lỗi, Admin.
