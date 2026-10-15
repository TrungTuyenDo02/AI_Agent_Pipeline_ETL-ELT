# Bản vá nhanh khi nguồn đổi cấu trúc

- Ngày chạy: 2026-10-16 • nguồn thử DuckDB (seed 42, 3 nguồn × 120 dòng) • `python eval/run_patch.py` • Codegen/Testgen của bản vá gọi LLM THẬT (pipeline gốc dựng bằng mock)
- Mỗi kịch bản: áp thay đổi lên bảng raw → kế hoạch vá (`patch_plan.build_plan`) → profiler → `patch_apply` → testgen → V1 → V2 → `patch_verify` (so bảng đích với lần chạy gốc).
- Cách cũ để so: tạo run mới và lập kế hoạch lại từ đầu, tốn một run đầy đủ. Mock không đếm token nên số của cách cũ lấy từ phép đo LLM thật ở bộ golden.

**Cần sửa code: 5/6 kịch bản • xử lý xong, qua V1+V2: 5/5 • bảng đích giống lần chạy gốc: 5/6 • cần AI hoặc người: 0 • V1/V2 chặn: 0**
Token của các bản vá chạy ở đây: **8327**. Cách cũ (tạo run mới, lập kế hoạch lại) tốn một run đầy đủ: trung bình **6918 token ≈ 0.0045 USD** mỗi run (LLM thật, đo ở bộ golden, `eval/results/golden_agent.md`), chưa kể các câu hỏi lại và lần duyệt kế hoạch.

| # | Kịch bản | Thay đổi phát hiện | Xử lý | Lựa chọn của người dùng | File sửa | Token (USD) | Kết quả |
|---|---|---|---|---|---|---|---|
| 1 | Đổi tên cột order_date → ordered_at (shopee_orders) | breaking: possible_rename | code | chọn cột nghi đổi tên | models/staging/stg_shopee_orders.sql<br>tests/assert_fct_daily_revenue_reconciles.sql | 0 (0) | Vá xong, bảng đích GIỐNG lần chạy gốc |
| 2 | Đổi tên cột VÀ đổi kiểu (website_orders.amount_vnd → amount, số → chuỗi) | breaking: column_removed<br>info: column_added | code, none | chọn cột amount thay amount_vnd | models/staging/stg_website_orders.sql<br>tests/assert_fct_daily_revenue_reconciles.sql | 0 (0) | Vá xong, bảng đích GIỐNG lần chạy gốc |
| 3 | Cột tiền từ chuỗi sang số (shopee_orders.total_amount) | breaking: type_incompatible | code | — | —<br>đã đúng sẵn: models/staging/stg_shopee_orders.sql, tests/assert_fct_daily_revenue_reconciles.sql | 0 (0) | Vá xong, bảng đích GIỐNG lần chạy gốc |
| 4 | Kiểu số thực đổi thành chuỗi (tiki_orders.grand_total) | breaking: type_incompatible | code | — | models/staging/stg_tiki_orders.sql<br>tests/assert_fct_daily_revenue_reconciles.sql | 0 (0) | Vá xong, bảng đích GIỐNG lần chạy gốc |
| 5 | Thêm cột mới (website_orders.channel) | info: column_added | none | — | — | 0 (0) | Vá xong, bảng đích GIỐNG lần chạy gốc |
| 6 | Xóa cột đang dùng (tiki_orders.grand_total) | breaking: column_removed | llm | chọn bỏ cột khỏi pipeline | — | 8327 (0.00269) | Vá xong, bảng đích KHÁC lần chạy gốc (hiện cho người duyệt) — 60 dòng khác (30 → 30) |

Ghi chú:
- Xử lý: `none` = không cần sửa code, `code` = sửa tất định bằng sqlglot, `llm` = cần AI, `ask` = cần người chọn, `blocked` = không vá được.
- "đã đúng sẵn": pipeline sinh ra đã ép kiểu cột đó ở staging (luật phòng thủ của giai đoạn 5) nên đổi kiểu ở nguồn không làm hỏng gì; bản vá không đổi file đó.
- Nếu bảng đích khác lần chạy gốc (nguồn mất giá trị khi đổi kiểu, hoặc dữ liệu đã đổi), `patch_verify` đưa sự khác biệt lên màn duyệt J2 thay vì im lặng.
- Kịch bản cần AI (bỏ cột đang dùng) không chạy ở đây: với LLM thật, ngữ cảnh chỉ gồm tên cột/kiểu và đúng các file cần sửa.
- Đây là mô phỏng trên sandbox, không phải trên nguồn production.
