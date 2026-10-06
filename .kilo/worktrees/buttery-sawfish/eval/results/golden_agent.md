# Bộ golden — chế độ `agent`

- Ngày chạy: 2026-10-02 • provider/model: openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- 12 ca trong eval/datasets/golden (dữ liệu nhỏ, kết quả đúng tính tay + kiểm bằng SQL chuẩn).

**Đạt: 12/12 ca**

| Ca | ok | mode_ok | asked | v_failures | tokens | cost_usd | seconds | detail |
|---|---|---|---|---|---|---|---|---|
| g01_three_sources | True | True | 0 | 0 | 10537 | 0.00513 | 45.8 | Khớp 3 dòng |
| g02_duplicate_rows | True | True | 0 | 1 | 12621 | 0.014623 | 56.2 | Khớp 2 dòng |
| g03_refunds | True | True | 0 | 0 | 7189 | 0.003835 | 36.3 | Khớp 2 dòng |
| g04_mixed_dates | True | True | 0 | 0 | 6893 | 0.003353 | 38.7 | Khớp 2 dòng |
| g05_vnd_format | True | True | 0 | 0 | 6838 | 0.003393 | 34.1 | Khớp 2 dòng |
| g06_one_to_many_join | True | True | 0 | 0 | 9624 | 0.005396 | 48.5 | Khớp 2 dòng |
| g07_null_amounts | True | True | 0 | 0 | 7137 | 0.003785 | 37.3 | Khớp 2 dòng |
| g08_cross_source_keys | True | True | 0 | 0 | 8670 | 0.004302 | 38.9 | Khớp 2 dòng |
| g09_customer_dimension | True | True | 0 | 1 | 13253 | 0.011931 | 82.0 | Khớp 3 dòng |
| g10_ambiguous_request | True | True | 2 | 0 | 6778 | 0.004089 | 31.0 | đã hỏi 2 câu làm rõ |
| g11_monthly_by_channel | True | True | 0 | 0 | 6983 | 0.003498 | 36.0 | Khớp 3 dòng |
| g12_pii_etl | True | True | 0 | 0 | 5833 | 0.002799 | 32.8 | Khớp 2 dòng |
