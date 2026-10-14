# Cửa kiểm tra đầu vào — tầng 0–1 (code) và tầng 2 (model nhỏ)

50 câu mẫu ([input_gate_cases.jsonl](../input_gate_cases.jsonl), 10 câu mỗi nhãn, do tác giả viết), danh mục = kho P113 Retail sinh tạm. Cột **có tầng 2** dùng LLM `mock` (**mô phỏng**: luật từ khóa giả lập, chưa đo bằng LLM thật).
Số lượt gọi LLM trong cả bộ: **10** (chỉ cho câu tầng 1 chưa chắc); tầng 0–1 gọi **0** lượt.

| Chỉ số | Chỉ tầng 0–1 | Có tầng 2 | Ngưỡng |
|---|---|---|---|
| Chặn nhầm câu hợp lệ | **0.0% (0/10)** | **0.0% (0/10)** | ≤ 2% |
| Lọt câu vô nghĩa | 0.0% (0/10) | 0.0% (0/10) | 0% |
| Lọt câu tấn công prompt | 0.0% (0/10) | 0.0% (0/10) | 0% |
| Lọt câu lạc đề | 0.0% (0/10) | 0.0% (0/10) | giảm so với chỉ tầng 0–1 |
| Câu mơ hồ bị chặn (nên cho qua để hỏi làm rõ) | 0.0% (0/10) | 0.0% (0/10) | 0% |

Cột chỉ tầng 0–1 tính `unclear` là bị chặn (cách của giai đoạn 1). Cột có tầng 2: chỉ `ok` mới cho qua; `needs_info` (xin viết lại/bổ sung, chưa phải từ chối thẳng) vẫn tính là chưa qua.

## Chi phí tầng 2 (ước tính)

- Model: `claude-haiku-5-5`; trung bình **397 token vào** (system + schema + tên bảng + câu hỏi, tiktoken) và ≤ 30 token ra → **≈ 0.000055 USD mỗi lần gọi** (10 câu tính trung bình).
- So với một lần chạy đầy đủ ≈ 0.0045 USD (golden 12 ca, LLM thật, 2026-10-08): **1.2%** (ngưỡng < 5%).
- Đây là ước tính theo bảng giá, không phải số đo từ nhà cung cấp.

## Chi tiết theo nhãn (có tầng 2)

| Nhãn | Số câu | Chưa qua | Dừng ở |
|---|---|---|---|
| valid | 10 | 0 | — |
| ambiguous | 10 | 0 | — |
| nonsense | 10 | 10 | tầng 0 (empty): 1, tầng 0 (keyboard_mash): 3, tầng 0 (low_alnum): 2, tầng 0 (repetitive): 3, tầng 0 (too_short): 1 |
| off_topic | 10 | 10 | tầng 2 (off_topic): 10 |
| attack | 10 | 10 | tầng 0 (attack): 10 |

## Câu phân loại sai (cột có tầng 2)

Không có.
