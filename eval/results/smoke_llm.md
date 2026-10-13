# Smoke test LLM thật (U2)

- Ngày chạy: 2026-10-13 • provider/model cấu hình: openai/planner=gpt-6-luna, codegen=gpt-6-luna, testgen=gpt-6-luna, optimizer=claude-opus-5-5
- Structured output: bật • prompt v2 • 3 yêu cầu golden (dữ liệu nhỏ).
- Luồng: Planner (tự chọn đáp án J1 như eval) → V0 → nạp nguồn → soi dữ liệu → Codegen → V1 (code, 0 token).
- Chi phí là ƯỚC TÍNH theo bảng giá trong `src/services/cost.py`, chưa trừ giảm giá cache.

| Ca | Lượt Planner | V0 | V1 | Thời gian |
|---|---:|---|---|---:|
| g01_three_sources | 1 | đạt | đạt | 32.2 s |
| g06_one_to_many_join | 1 | đạt | đạt | 36.0 s |
| g09_customer_dimension | 1 | đạt | đạt | 26.3 s |

Câu hỏi làm rõ Planner đặt ra (ca golden đều đã nói rõ, kỳ vọng không hỏi):

- (không hỏi câu nào)

| Ca | Bước | Provider trả lời | Model | Token vào | Trúng cache | Token ra | Chi phí (USD) | Thời gian |
|---|---|---|---|---:|---:|---:|---:|---:|
| g01_three_sources | planner | openai | gpt-6-luna | 1572 | 0 | 1363 | 0.000839 | 11.7 s |
| g01_three_sources | codegen | openai | gpt-6-luna | 1700 | 0 | 1756 | 0.001048 | 17.2 s |
| g06_one_to_many_join | planner | openai | gpt-6-luna | 1521 | 1183 | 2035 | 0.001170 | 16.8 s |
| g06_one_to_many_join | codegen | openai | gpt-6-luna | 1541 | 0 | 1680 | 0.000994 | 18.3 s |
| g09_customer_dimension | planner | openai | gpt-6-luna | 1464 | 1183 | 1515 | 0.000904 | 12.4 s |
| g09_customer_dimension | codegen | openai | gpt-6-luna | 1336 | 0 | 1365 | 0.000816 | 13.3 s |

**Tổng:** 6 lần gọi • 9134 token vào • 9714 token ra • 0.005771 USD • tỉ lệ token vào trúng cache: 25.9% • số lần phải chuyển dự phòng Gemini: 0
