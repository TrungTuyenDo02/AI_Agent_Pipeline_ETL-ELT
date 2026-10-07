# Bộ golden — chế độ `reference`

- Ngày chạy: 2026-10-07 • provider/model: openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- 12 ca trong eval/datasets/golden (dữ liệu nhỏ, kết quả đúng tính tay + kiểm bằng SQL chuẩn).

**Đạt: 11/11 ca**

| Ca | ok | detail |
|---|---|---|
| g01_three_sources | True | Khớp 3 dòng |
| g02_duplicate_rows | True | Khớp 2 dòng |
| g03_refunds | True | Khớp 2 dòng |
| g04_mixed_dates | True | Khớp 2 dòng |
| g05_vnd_format | True | Khớp 2 dòng |
| g06_one_to_many_join | True | Khớp 2 dòng |
| g07_null_amounts | True | Khớp 2 dòng |
| g08_cross_source_keys | True | Khớp 2 dòng |
| g09_customer_dimension | True | Khớp 3 dòng |
| g11_monthly_by_channel | True | Khớp 3 dòng |
| g12_pii_etl | True | Khớp 2 dòng |
