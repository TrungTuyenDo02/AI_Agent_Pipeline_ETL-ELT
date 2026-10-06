# ADR 0002 — CLI bằng argparse; nhà cung cấp LLM `mock` mặc định

- Ngày: 2026-10-02 • Trạng thái: Chấp nhận

## Bối cảnh
Giai đoạn A phải chạy trọn luồng trong terminal khi chưa có khóa LLM.

## Quyết định
- CLI dùng `argparse` (thư viện chuẩn): đủ cho ~8 lệnh con, không thêm dependency. Hiển thị bằng `rich`.
- `LLM_PROVIDER=mock` mặc định: câu trả lời cố định theo từng node (`src/services/llm_mock.py`), 0 token,
  đánh dấu `simulated=True`; giao diện luôn hiện nhãn "Chế độ mô phỏng".

## Hệ quả
- Test/CI/demo chạy không cần khóa, không cần mạng.
- Số liệu chất lượng LLM khi chạy mock **không** được trình bày như năng lực mô hình thật. Số đo của V-node
  (dbt test, đối chiếu, thời gian query) vẫn là đo thật.
