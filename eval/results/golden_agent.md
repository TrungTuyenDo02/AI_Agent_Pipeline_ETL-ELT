# Bộ golden — chế độ `agent`

- Ngày chạy: 2026-10-05 • provider/model: openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- 12 ca trong eval/datasets/golden (dữ liệu nhỏ, kết quả đúng tính tay + kiểm bằng SQL chuẩn).

**Đạt: 12/12 ca**

| Ca | ok | mode_ok | asked | v_failures | tokens | input_tokens | cached_tokens | cost_usd | seconds | detail |
|---|---|---|---|---|---|---|---|---|---|---|
| g01_three_sources | True | True | 0 | 0 | 10037 | 5989 | 1556 | 0.006055 | 51.1 | Khớp 3 dòng |
| g02_duplicate_rows | True | True | 0 | 0 | 11297 | 6524 | 1337 | 0.023849 | 61.4 | Khớp 2 dòng |
| g03_refunds | True | True | 0 | 0 | 7158 | 4290 | 1327 | 0.0043 | 39.3 | Khớp 2 dòng |
| g04_mixed_dates | True | True | 0 | 0 | 7500 | 4404 | 1327 | 0.004596 | 42.4 | Khớp 2 dòng |
| g05_vnd_format | True | True | 0 | 0 | 7390 | 4696 | 1357 | 0.004172 | 38.7 | Khớp 2 dòng |
| g06_one_to_many_join | True | True | 0 | 0 | 8116 | 4897 | 1416 | 0.004843 | 45.6 | Khớp 2 dòng |
| g07_null_amounts | True | True | 0 | 0 | 6824 | 4278 | 1337 | 0.003911 | 36.4 | Khớp 2 dòng |
| g08_cross_source_keys | True | True | 0 | 0 | 8992 | 5153 | 1404 | 0.005637 | 71.8 | Khớp 2 dòng |
| g09_customer_dimension | True | True | 0 | 1 | 11214 | 7622 | 1372 | 0.012016 | 80.2 | Khớp 3 dòng |
| g10_ambiguous_request | True | True | 2 | 0 | 13397 | 7872 | 4459 | 0.008205 | 69.6 | đã hỏi 2 câu làm rõ |
| g11_monthly_by_channel | True | True | 0 | 0 | 6647 | 4137 | 1298 | 0.00384 | 38.5 | Khớp 3 dòng |
| g12_pii_etl | True | True | 0 | 0 | 5419 | 3599 | 1278 | 0.002904 | 30.0 | Khớp 2 dòng |
