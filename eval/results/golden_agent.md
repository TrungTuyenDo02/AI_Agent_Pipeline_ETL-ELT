# Bộ golden — chế độ `agent`

- Ngày chạy: 2026-10-08 • provider/model: openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- 12 ca trong eval/datasets/golden (dữ liệu nhỏ, kết quả đúng tính tay + kiểm bằng SQL chuẩn).

**Đạt: 12/12 ca**

| Ca | ok | mode_ok | asked | v_failures | tokens | input_tokens | cached_tokens | cost_usd | seconds | detail |
|---|---|---|---|---|---|---|---|---|---|---|
| g01_three_sources | True | True | 0 | 0 | 7999 | 5152 | 0 | 0.004448 | 53.9 | Khớp 3 dòng |
| g02_duplicate_rows | True | True | 0 | 0 | 7413 | 3987 | 1060 | 0.004909 | 51.1 | Khớp 2 dòng |
| g03_refunds | True | True | 0 | 0 | 6116 | 3895 | 1060 | 0.003444 | 46.0 | Khớp 2 dòng |
| g04_mixed_dates | True | True | 0 | 0 | 6202 | 3907 | 1060 | 0.003535 | 39.4 | Khớp 2 dòng |
| g05_vnd_format | True | True | 0 | 0 | 6403 | 4165 | 1060 | 0.003518 | 38.4 | Khớp 2 dòng |
| g06_one_to_many_join | True | True | 0 | 0 | 8032 | 4512 | 1060 | 0.005127 | 51.8 | Khớp 2 dòng |
| g07_null_amounts | True | True | 0 | 0 | 6235 | 3867 | 1060 | 0.003615 | 41.6 | Khớp 2 dòng |
| g08_cross_source_keys | True | True | 0 | 0 | 7377 | 4526 | 1060 | 0.004326 | 50.2 | Khớp 2 dòng |
| g09_customer_dimension | True | True | 0 | 0 | 8393 | 5015 | 1060 | 0.010689 | 66.8 | Khớp 3 dòng |
| g10_ambiguous_request | True | True | 2 | 0 | 7617 | 4955 | 2120 | 0.004185 | 42.4 | đã hỏi 2 câu làm rõ |
| g11_monthly_by_channel | True | True | 0 | 0 | 5994 | 3860 | 1060 | 0.003333 | 39.9 | Khớp 3 dòng |
| g12_pii_etl | True | True | 0 | 0 | 5231 | 3444 | 1060 | 0.002834 | 35.0 | Khớp 2 dòng |
