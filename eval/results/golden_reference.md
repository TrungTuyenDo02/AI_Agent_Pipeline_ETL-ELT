# Bộ golden — chế độ `reference`

- Ngày chạy: 2026-10-16 • provider/model: openai/planner=gpt-6-luna, codegen=gpt-6-luna, testgen=gpt-6-luna, optimizer=claude-haiku-5-5
- 17 ca trong eval/datasets/golden (dữ liệu nhỏ, kết quả đúng tính tay + kiểm bằng SQL chuẩn).

**Đạt: 16/16 ca**

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
| g13_gloss_revenue | True | Khớp 2 dòng |
| g14_gloss_refunds | True | Khớp 2 dòng |
| g15_gloss_cancelled | True | Khớp 1 dòng |
| g16_gloss_duplicates | True | Khớp 2 dòng |
| g17_gloss_aov | True | Khớp 2 dòng |
