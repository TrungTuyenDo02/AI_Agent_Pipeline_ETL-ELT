# ADR 0011 — Từ điển nghiệp vụ (business glossary)

- Ngày: 2026-10-16 • Trạng thái: chấp nhận

## Bối cảnh

Người dùng viết yêu cầu bằng từ của công ty ("doanh thu", "đơn hoàn tất", "trùng đơn") mà không nêu điều kiện cụ thể. Planner phải đoán hoặc
hỏi lại; cửa kiểm tra tầng 1 chỉ biết tên bảng/cột nên dễ chặn nhầm hoặc đẩy sang tầng 2 tốn token.

## Quyết định

- Bảng `glossary_terms` (migration 0007): thuật ngữ, từ đồng nghĩa, định nghĩa, `maps_to`, `department_id` (trống = dùng chung). **Chỉ Admin ghi**
  (API và web); mã của agent không gọi hàm ghi (có test quét). Định nghĩa là chữ do người viết, không chứa dữ liệu thật.
- Seed từ `config/glossary_seed.yaml` (17 thuật ngữ P113 Retail). File này cũng là từ điển chỉ đọc khi không có cơ sở dữ liệu ứng dụng (CLI demo, eval offline).
- **Đường vào prompt duy nhất:** `build_llm_context(..., glossary=True).glossary_for(yêu cầu)` — khớp nguyên cụm, bỏ dấu, nhiều chữ nhất trước, tối đa
  `GLOSSARY_MAX_TERMS` (mặc định 3); định nghĩa cắt 200 ký tự; phần `maps_to` nhắc bảng người dùng không được thấy bị ẩn (không lộ bảng ngoài quyền).
  Đoạn mô tả bảng đích/cột đầu ra ("Bảng đích …, các cột: …") không dùng để khớp vì nhắc "số đơn", "ngày đặt đơn" ở mọi yêu cầu (đo: token +17,8% → +13,5%).
- Thuật ngữ đã đưa vào prompt do **code** ghi vào `spec.glossary_used` (không nhờ LLM kể) và hiện ở J1b ("Thuật ngữ đã dùng").
- Tầng 1 của cửa kiểm tra nhận thuật ngữ + từ đồng nghĩa làm từ khóa, nhưng chỉ cụm nhiều chữ hoặc từ đơn dài từ 5 ký tự (không tách từng chữ như tên cột) để từ thường ngày
  ("kênh", "đồng") không làm lọt câu lạc đề.

## Hệ quả

- Token prompt Planner tăng 13,5% trên 17 ca golden (trần 15%); phần tĩnh +52 token (budget planner 1.400).
- Độ đúng trước/sau cần LLM thật nên chưa đo (chủ dự án chọn chỉ dùng mô phỏng); chỉ đo được phần code (chọn đúng thuật ngữ: 6/6 ở 5 ca mới).
- Một định nghĩa sai là một nguồn sai chung cho cả phòng ban: Admin chịu trách nhiệm nội dung, mọi sửa đều ghi AuditLog.
