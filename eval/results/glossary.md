# Từ điển nghiệp vụ: đo không gọi LLM

17 ca golden ([eval/datasets/golden](../datasets/golden)): 12 ca cũ + 5 ca mới có yêu cầu viết bằng thuật ngữ công ty, không nêu trạng thái (g13–g17). Từ điển mẫu: 17 thuật ngữ cho P113 Retail ([config/glossary_seed.yaml](../../config/glossary_seed.yaml)). **Không gọi LLM**: chỉ đo phần code (chọn thuật ngữ, kích thước prompt).

| Chỉ số | Kết quả | Tiêu chí |
|---|---|---|
| Thuật ngữ cần thiết tới được Planner (ca mới) | **6/6** | tất cả |
| Thuật ngữ đưa vào 12 ca cũ (đã nêu rõ điều kiện, không bắt buộc) | 30 | thông tin, không phải lỗi |
| Token prompt Planner tăng (v10 có thuật ngữ so với v9, trung bình 17 ca) | **+13.5%** | ≤ 15% |

## Từng ca

| Ca | Thuật ngữ cần | Thuật ngữ được đưa vào | Token (v10 không có thuật ngữ) | Token (v10 có thuật ngữ) |
|---|---|---|---|---|
| g01_three_sources | — | doanh thu theo ngày, doanh thu | 1179 | 1280 |
| g02_duplicate_rows | — | doanh thu theo ngày, doanh thu, mã đơn | 1105 | 1206 |
| g03_refunds | — | doanh thu, hoàn tiền | 1092 | 1159 |
| g04_mixed_dates | — | doanh thu theo ngày, ngày đặt đơn, doanh thu | 1102 | 1200 |
| g05_vnd_format | — | doanh thu theo ngày, doanh thu, tiền VND | 1126 | 1237 |
| g06_one_to_many_join | — | số đơn, doanh thu, tiền VND | 1160 | 1279 |
| g07_null_amounts | — | doanh thu theo ngày, đơn thiếu số tiền, doanh thu | 1104 | 1217 |
| g08_cross_source_keys | — | doanh thu theo ngày, doanh thu, mã đơn | 1147 | 1248 |
| g09_customer_dimension | — | khách hàng, số đơn, tiền VND | 1109 | 1232 |
| g10_ambiguous_request | — | doanh thu | 1022 | 1055 |
| g11_monthly_by_channel | — | doanh thu theo tháng, doanh thu, kênh bán | 1073 | 1189 |
| g12_pii_etl | — | khách hàng | 1067 | 1105 |
| g13_gloss_revenue | doanh thu | doanh thu theo ngày, doanh thu | 1071 | 1139 |
| g14_gloss_refunds | hoàn tiền | hoàn tiền, số đơn | 1077 | 1152 |
| g15_gloss_cancelled | đơn hủy | đơn hủy, số đơn | 1083 | 1156 |
| g16_gloss_duplicates | trùng đơn, doanh thu | doanh thu theo ngày, doanh thu, trùng đơn | 1079 | 1182 |
| g17_gloss_aov | giá trị đơn trung bình | giá trị đơn trung bình, trùng đơn | 1070 | 1145 |

Token v9 ước tính = token v10 không có thuật ngữ − 52 (phần tĩnh thêm của khối `glossary` và quy tắc 16).

## Chưa đo: độ đúng của agent trước/sau khi có từ điển

Câu hỏi "có từ điển thì Planner đoán đúng điều kiện (trạng thái, trùng đơn, đơn vị) hơn không" cần chạy agent bằng LLM thật. Theo lựa chọn của người dùng, đợt này chỉ dùng chế độ mô phỏng (LLM giả không đọc ngữ cảnh), nên **độ đúng chưa được đo**.
Lệnh đo (ước tính ≈ 5 ca mới × 2 lần × 0,0045 USD ≈ 0,05 USD, theo chi phí golden 2026-10-08):

```bash
# trước: GLOSSARY_MAX_TERMS=0 (không đưa thuật ngữ vào prompt); sau: mặc định
LLM_PROVIDER=openai GLOSSARY_MAX_TERMS=0 python eval/run_eval.py --with-llm
LLM_PROVIDER=openai python eval/run_eval.py --with-llm
```

Tiêu chí nghiệm thu của CLAUDE.md (giai đoạn 6): độ đúng sau ≥ trước; token prompt Planner tăng ≤ 15%.
