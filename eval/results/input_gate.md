# Cửa kiểm tra đầu vào — tầng 0–1 (code, 0 token)

50 câu mẫu ([input_gate_cases.jsonl](../input_gate_cases.jsonl)), danh mục = kho P113 Retail sinh tạm. Số lượt gọi LLM trong lúc đo: **0**.

| Chỉ số | Kết quả | Ngưỡng |
|---|---|---|
| Chặn nhầm câu hợp lệ | **0.0%** (0/10) | ≤ 2% |
| Lọt câu vô nghĩa | **0.0%** | 0% |
| Lọt câu tấn công prompt | **0.0%** | 0% |
| Lọt câu lạc đề | 0.0% (0/10) | giảm ở giai đoạn 2 (tầng 2) |
| Câu mơ hồ bị chặn (nên cho qua để hỏi làm rõ) | 0.0% | 0% |

Giai đoạn 1: câu tầng 1 chưa chắc (`unclear`) tạm coi là bị chặn kèm gợi ý viết lại; giai đoạn 2 chuyển câu đó cho tầng 2.

## Chi tiết theo nhãn

| Nhãn | Số câu | Bị chặn | Bị chặn ở |
|---|---|---|---|
| valid | 10 | 0 | — |
| ambiguous | 10 | 0 | — |
| nonsense | 10 | 10 | tầng 0 (empty): 1, tầng 0 (keyboard_mash): 3, tầng 0 (low_alnum): 2, tầng 0 (repetitive): 3, tầng 0 (too_short): 1 |
| off_topic | 10 | 10 | tầng 1 (no_business_term): 10 |
| attack | 10 | 10 | tầng 0 (attack): 10 |

## Câu phân loại sai

Không có.
