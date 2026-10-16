> Đọc `docs/specs/v2/00-chung.md` trước.

## 7. Việc cuối cùng sau khi xong giai đoạn 1–6

1. Cập nhật `README.md`: mục "Giải pháp" (cửa kiểm tra đầu vào, mức truy cập dữ liệu, phát hiện thay đổi cấu trúc), đoạn "Dữ liệu đi đâu", bảng API, bảng màn hình web (thêm "Nguồn dữ liệu", "Thay đổi cấu trúc"), "Hạn chế đã biết" (liệt kê các mục ngoài phạm vi ở 0.6 và nói rõ: hệ thống phát hiện thay đổi nhưng không ngăn được; cần hợp đồng dữ liệu giữa các đội), sơ đồ kiến trúc có thêm khối **Cửa kiểm tra**, **Sổ nguồn**, **Giám sát cấu trúc**.
2. Sửa các điểm README đang lệch thực tế: tên model LLM hiện đang dùng, huy hiệu CI trỏ đúng repo, đánh dấu lại mục "Evaluation evidence".
3. Cập nhật `docs/RUNBOOK.md`: cách đăng ký nguồn, cách đặt mức truy cập, cách chạy Postgres thử, cách đặt lịch kiểm tra cấu trúc, các biến môi trường mới.
4. Chạy `python scripts/tasks.py ci` và `make eval`; ghi số đo mới vào `eval/results/report.md`.
5. Báo cáo cho người dùng: đã làm gì ở từng giai đoạn, số đo trước/sau, điều gì chưa làm được và vì sao.


## 8. Khi gặp điều chưa rõ

- Nếu một yêu cầu trong tài liệu này mâu thuẫn với code hiện có, **dừng và hỏi** thay vì tự quyết.
- Không thêm thư viện mới nặng nề khi chưa cần; nếu cần (ví dụ driver Postgres), chọn gói phổ biến, ghi vào `requirements.txt` và nêu lý do trong `WORKLOG.md`.
- Không tự bật tính năng tốn tiền (gọi LLM thật hàng loạt) khi chưa báo trước số tiền ước tính.
