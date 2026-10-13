# Kịch bản video demo (tối đa 5 phút)

> Đây là **kịch bản quay**. Việc quay và dựng video là của người trình bày. Sau khi có video, ghi link vào [README.md](../README.md)
> và tick mục "Video demo" trong Deliverables.

**Chuẩn bị trước khi bấm quay (5 phút):**
1. Chế độ mô phỏng, không cần khóa: `docker compose up -d db`, `alembic upgrade head`, `python -m src.cli users seed-dev` (ghi lại mật khẩu in ra).
2. `python scripts/tasks.py run` và `python scripts/tasks.py frontend-dev`. Mở `http://localhost:3000`.
3. Đăng nhập sẵn **hai cửa sổ trình duyệt**: một bằng `an` (Engineer), một bằng `binh` (Reviewer). Chữ trình duyệt cỡ 125%, tắt thông báo hệ thống.
4. Tạo trước một lần chạy đã xong tới bước chờ duyệt để dự phòng nếu mạng/máy chậm.
5. Ghi âm thử 10 giây để kiểm tra micro.

## Bảng thời gian

| Giờ | Ai nói / làm | Màn hình | Lời thoại gợi ý (đọc chậm, đời thường) |
|---|---|---|---|
| 0:00–0:30 | Người dẫn | Trang chủ Engineer | "Data engineer mất nhiều giờ viết đi viết lại pipeline dbt và Airflow, rồi vẫn lo dữ liệu bẩn làm sai số. Công cụ viết code thường không chạy thử và tự báo xong mà không có bằng chứng. P-113 làm khác: **người phán đoán, agent làm việc, code thuần kiểm chứng**." |
| 0:30–1:00 | Engineer `an` | Ô "Mô tả pipeline bạn cần" | Gõ: *Gộp dữ liệu đơn hàng 3 nguồn (Shopee CSV, Tiki JSON, website SQLite), tính doanh thu theo ngày* → bấm **Gửi**. "Agent chưa vội viết code, nó hỏi lại điều chưa rõ." |
| 1:00–1:40 | Engineer | Màn lần chạy, bước **Làm rõ** rồi **Kế hoạch** | Chọn đáp án (đơn nào tính doanh thu, đơn trùng xử lý sao). Chỉ vào kế hoạch: "Mỗi bước có giải thích *vì sao*. Mình đọc và đồng ý **trước khi** tốn công sinh code." Bấm **Đồng ý**. |
| 1:40–2:20 | Engineer | Thanh tiến trình E/V/J và bước **Chạy và kiểm chứng** | "Tròn là agent, vuông là code kiểm chứng, thoi là con người. Các ô vuông không dùng AI nên không bịa được: chặn lệnh nguy hiểm, chạy thử thật trong hộp cát DuckDB, đối chiếu kết quả." Chờ các bước xanh. |
| 2:20–3:20 | Reviewer `binh` | Màn **Duyệt**: khung "Bằng chứng" | "Bên trái là **số do code đo**, bên phải là **lời agent nói** và có nhãn *chưa kiểm chứng*." Cuộn danh sách đo: 3/3 test đạt, đối chiếu từng bộ dữ liệu giống hệt. Bấm tab **Code sinh ra** để cho thấy code dbt, chỉ vào dòng bị tô vàng (điều kiện lọc cứng). |
| 3:20–3:50 | Reviewer | Tab **Tối ưu** | "Tối ưu chỉ áp dụng khi *đáng*: nhanh hơn ngưỡng 15% và kết quả giống hệt trên 5 bộ dữ liệu. Không đáng thì ghi *giữ nguyên* kèm lý do." |
| 3:50–4:20 | Reviewer | Nút **Duyệt**, rồi **Tải gói code (.zip)** | "Người duyệt bấm duyệt, tải gói code để tự mở Pull Request. Agent không tự đẩy code." |
| 4:20–4:50 | Người dẫn | Trang `eval/results/report.md` hoặc slide số liệu | "Đo thật: bộ 12 ca golden đúng 12/12 với LLM thật; kiểm thử đột biến bắt 11/12 lỗi giả; TPC-H 11/13 query chậm được tối ưu mà không đổi kết quả. Mỗi con số ghi điều kiện đo." |
| 4:50–5:00 | Người dẫn | Màn hình tên dự án + link repo | "Hạn chế thật: chạy trên dữ liệu giả lập, chưa có DE làm tay để so sánh. Cảm ơn đã xem." |

## Gợi ý khi quay

- Mỗi cảnh quay một lần rồi ghép; không cố quay liền 5 phút.
- Nếu một bước chờ lâu (chế độ mô phỏng mất vài chục giây), cắt đoạn chờ khi dựng và để lại thanh tiến trình nhích để người xem thấy hệ thống đang làm việc thật.
- Không để lộ mật khẩu tài khoản mẫu, khóa API hay nội dung `.env` trên màn hình.
- Phụ đề tiếng Việt cho các thuật ngữ: *agent* (trợ lý tự làm việc), *sandbox* (hộp cát chạy thử), *mutation test* (cố tình cài lỗi giả để xem bộ kiểm có bắt được không).

## Danh sách kiểm (khớp [presentation/README.md](../presentation/README.md))

- [ ] Giới thiệu vấn đề (< 30 giây)
- [ ] Demo tính năng chính (2–3 phút)
- [ ] Kết quả của AI (1 phút)
- [ ] Tóm tắt tác động (< 30 giây)
- [ ] Tệp video đặt tên `video_demo.mp4` trong `presentation/` hoặc link tải lên và ghi vào README
