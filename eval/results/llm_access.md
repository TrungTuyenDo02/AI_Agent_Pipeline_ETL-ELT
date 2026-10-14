# Mức truy cập dữ liệu của LLM: `schema_only` so với `profile`

12 ca golden ([eval/datasets/golden](../datasets/golden)), mỗi ca dùng dữ liệu nguồn của chính nó (đăng ký ở sổ nguồn mặc định, độ nhạy cảm `medium`). **Không gọi LLM**: chỉ đo ngữ cảnh dữ liệu mà code đưa vào prompt (tiktoken `o200k_base`, đúng chuỗi JSON gửi đi).

| Chỉ số | `schema_only` | `profile` (mặc định) |
|---|---|---|
| Token ngữ cảnh Planner (tổng 12 ca) | 562 | 1862 |
| Token hồ sơ cho Codegen/Testgen (tổng 12 ca) | 635 | 2416 |
| Giá trị thật lọt vào ngữ cảnh | **0** | **0** |

## Từng ca

| Ca | Bảng | Planner `schema_only` | Planner `profile` | Hồ sơ `schema_only` | Hồ sơ `profile` | Lọt |
|---|---|---|---|---|---|---|
| g01_three_sources | 3 | 100 | 345 | 114 | 404 | 0 |
| g02_duplicate_rows | 1 | 35 | 114 | 39 | 170 | 0 |
| g03_refunds | 1 | 34 | 119 | 38 | 142 | 0 |
| g04_mixed_dates | 1 | 35 | 122 | 39 | 167 | 0 |
| g05_vnd_format | 1 | 35 | 122 | 39 | 251 | 0 |
| g06_one_to_many_join | 2 | 64 | 182 | 73 | 253 | 0 |
| g07_null_amounts | 1 | 34 | 112 | 38 | 142 | 0 |
| g08_cross_source_keys | 2 | 67 | 189 | 76 | 311 | 0 |
| g09_customer_dimension | 2 | 56 | 194 | 62 | 187 | 0 |
| g10_ambiguous_request | 1 | 34 | 126 | 38 | 142 | 0 |
| g11_monthly_by_channel | 1 | 37 | 122 | 44 | 156 | 0 |
| g12_pii_etl | 1 | 31 | 115 | 35 | 91 | 0 |

## Chưa đo: độ đúng của agent theo từng mức

Câu hỏi "`profile` có giúp Planner sinh phép làm sạch đúng hơn `schema_only` không" cần chạy agent bằng LLM thật. Theo lựa chọn của người dùng, đợt này chỉ dùng chế độ mô phỏng (LLM giả không đọc ngữ cảnh nên cho cùng kết quả ở hai mức), nên **độ đúng chưa được đo**.
Lệnh đo (ước tính ≈ 12 ca × 0,0045 USD × 2 mức ≈ 0,11 USD, theo chi phí golden 2026-10-08):

```bash
LLM_PROVIDER=openai LLM_ACCESS_DEFAULT=schema_only python eval/run_eval.py --with-llm
LLM_PROVIDER=openai LLM_ACCESS_DEFAULT=profile python eval/run_eval.py --with-llm
```

Tiêu chí nghiệm thu của CLAUDE.md (giai đoạn 3): độ đúng ở `profile` không thấp hơn trước khi đổi (golden 12/12 ngày 2026-10-08).
