# Schema drift — 6 kịch bản "backend đổi nguồn không báo"

- Ngày chạy: 2026-10-14 • nguồn thử DuckDB (seed 42, 3 nguồn × 120 dòng) • pipeline sinh bằng mock • `python scripts/simulate_drift.py`
- Mỗi kịch bản: áp thay đổi lên bảng raw → bộ phát hiện (`schema_drift`) → chạy lại pipeline đã sinh (preflight + dbt build + test) → so bảng đích với bản gốc.
- Phạm vi: đây là mô phỏng trên sandbox, không phải trên cơ sở dữ liệu production; không có LLM, không có mạng.

**Chặn hoặc fail sớm: 4/6** • vô hại, vẫn đúng: 1 • chỉ cảnh báo thống kê: 1 • **sai nhưng báo thành công mà không có tín hiệu nào: 0**.
Báo nhầm (không đổi gì mà vẫn có thay đổi, hoặc kịch bản vô hại bị chặn): 0 • thời gian phát hiện trung bình: 0.29 giây (đo sau khi áp thay đổi, trên dữ liệu thử nhỏ).
Đối chứng (không đổi gì): 0 thay đổi, pipeline chạy xong, kết quả như gốc.

| # | Kịch bản | Cấu trúc (mức: loại) | Thống kê | Chặn trước run | Pipeline chạy lại | Phát hiện (s) |
|---|---|---|---|---|---|---|
| 1 | Cột tiền từ chuỗi sang số (shopee_orders.total_amount) | breaking: type_incompatible | stat_new_shape | có | fail sớm ở preflight — cau truc nguon da doi so voi luc sinh pipeline:; Cot shopee_orders.total_amount doi kieu: ky vong varchar, thuc te bigint. | 0.27 |
| 2 | Đổi tên cột order_date → ordered_at (shopee_orders) | breaking: possible_rename | — | có | fail sớm ở preflight — cau truc nguon da doi so voi luc sinh pipeline:; Cot shopee_orders.order_date khong con o nguon. | 0.31 |
| 3 | Xóa cột đang dùng (tiki_orders.grand_total) | breaking: column_removed | — | có | fail sớm ở preflight — cau truc nguon da doi so voi luc sinh pipeline:; Cot tiki_orders.grand_total khong con o nguon. | 0.27 |
| 4 | Thêm cột mới (website_orders.channel) | info: column_added | — | không | chạy xong, kết quả như gốc | 0.29 |
| 5 | Cột ngày bỗng rỗng nhiều (shopee_orders.order_date rỗng ~60%) | — | stat_null_increase | không | fail ở test dbt — d0b38a8c9d, fct_daily_revenue | 0.31 |
| 6 | Cột tiền đổi đơn vị ×1000 (shopee_orders.total_amount: 1.075.000 → 1.075.000.000) | — | stat_new_shape | không | chạy xong, KẾT QUẢ KHÁC GỐC | 0.29 |

Ghi chú:
- Kịch bản 6 (đổi đơn vị) không đổi cấu trúc: pipeline vẫn chạy xong với số khác. Hệ thống chỉ cảnh báo thống kê (`stat_new_shape`); đây là giới hạn đã nêu trong spec, cần người phán đoán.
- "Chặn trước run" = có thay đổi `breaking` → `drift_gate` dừng run trước Planner. "Pipeline chạy lại" = lớp phòng thủ thứ hai nằm trong pipeline đã sinh (preflight `check_source_schema`, test nguồn, test ép kiểu).
- Hệ thống phát hiện thay đổi, không ngăn được backend đổi; cần hợp đồng dữ liệu giữa các đội.
