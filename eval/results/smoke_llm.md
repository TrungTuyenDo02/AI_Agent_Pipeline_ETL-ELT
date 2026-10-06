# Smoke test LLM thật (U2)

- Ngày chạy: 2026-10-05 • provider/model cấu hình: openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- Structured output: bật • prompt v2 • 3 yêu cầu golden (dữ liệu nhỏ).
- Luồng: Planner (tự chọn đáp án J1 như eval) → V0 → nạp nguồn → soi dữ liệu → Codegen → V1 (code, 0 token).
- Chi phí là ƯỚC TÍNH theo bảng giá trong `src/services/cost.py`, chưa trừ giảm giá cache.

| Ca | Lượt Planner | V0 | V1 | Thời gian |
|---|---:|---|---|---:|
| g01_three_sources | 2 | đạt | đạt | 43.8 s |
| g06_one_to_many_join | 1 | đạt | đạt | 24.8 s |
| g09_customer_dimension | 1 | đạt | đạt | 24.4 s |

Câu hỏi làm rõ Planner đặt ra (ca golden đều đã nói rõ, kỳ vọng không hỏi):

- g01_three_sources: Nếu cùng một đơn hàng xuất hiện nhiều lần trong cùng nguồn hoặc giữa các nguồn, cần xử lý như thế nào? → Giữ tất cả bản ghi
- g01_three_sources: Khi chuyển dấu thời gian thành order_date, dùng múi giờ nào? → Giữ ngày theo giá trị thời gian trong nguồn

| Ca | Bước | Provider trả lời | Model | Token vào | Trúng cache | Token ra | Chi phí (USD) | Thời gian |
|---|---|---|---|---:|---:|---:|---:|---:|
| g01_three_sources | planner | openai | gpt-5.6-luna | 1475 | 1472 | 1825 | 0.002485 | 17.9 s |
| g01_three_sources | planner | openai | gpt-5.6-luna | 1554 | 0 | 1279 | 0.001846 | 12.2 s |
| g01_three_sources | codegen | openai | gpt-5.6-luna | 2203 | 0 | 1244 | 0.001933 | 10.7 s |
| g06_one_to_many_join | planner | openai | gpt-5.6-luna | 1335 | 1332 | 1200 | 0.001707 | 12.5 s |
| g06_one_to_many_join | codegen | openai | gpt-5.6-luna | 1822 | 0 | 1253 | 0.001868 | 11.8 s |
| g09_customer_dimension | planner | openai | gpt-5.6-luna | 1291 | 1288 | 1072 | 0.001545 | 11.5 s |
| g09_customer_dimension | codegen | openai | gpt-5.6-luna | 1660 | 0 | 1225 | 0.001802 | 12.5 s |

**Tổng:** 7 lần gọi • 11340 token vào • 9098 token ra • 0.013186 USD • tỉ lệ token vào trúng cache: 36.1% • số lần phải chuyển dự phòng Gemini: 0
