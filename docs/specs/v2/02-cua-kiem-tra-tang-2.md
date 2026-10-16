> Đọc `docs/specs/v2/00-chung.md` (quy tắc chung) trước khi làm giai đoạn này.

## 2. Giai đoạn 2 — Cửa kiểm tra tầng 2 (bộ phân loại model nhỏ)

**Mục tiêu:** xử lý các câu tầng 0–1 chưa chắc, bằng model rẻ nhất, câu trả lời cực ngắn.

- Chỉ chạy khi tầng 1 trả `unclear`. Mock provider phải có phiên bản giả lập quyết định được (dựa trên luật đơn giản) để CI chạy không cần khóa.
- Cấu hình model riêng `MODEL_GATE` (mặc định model rẻ nhất đang dùng, có thể là Gemini flash-lite). **Không** dùng model của planner/optimizer.
- Prompt đặt ở `src/prompts/input_gate.py`: yêu cầu trả **JSON** cố định: `{"label": "pipeline|optimize|off_topic|unclear", "confidence": 0-1, "missing": ["..."]}`. Giới hạn `max_tokens` thấp (≈ 100). Kiểm tra cấu trúc bằng Pydantic (`src/models/`); sai cấu trúc → coi là `unclear`, không thử lại quá 1 lần.
- Quy tắc quyết định:
  - `off_topic` và confidence ≥ 0.8 → từ chối kèm gợi ý.
  - `unclear` hoặc confidence thấp → **không từ chối thẳng**; yêu cầu người dùng viết lại kèm ví dụ (chặn nhầm gây khó chịu hơn tốn thêm vài đồng).
  - `pipeline`/`optimize` → cho qua Planner.
- Với yêu cầu đúng nghiệp vụ nhưng thiếu thông tin (`missing` không rỗng): hỏi bằng **mẫu câu cố định** ghép từ các ô còn thiếu, **không gọi LLM để soạn câu hỏi**.
- Ghi chi phí token của bước này vào bộ đếm `cost` hiện có, hiển thị riêng một dòng "kiểm tra đầu vào".
- Chạy lại `eval/run_input_gate.py` với LLM thật, ghi thêm cột "có tầng 2" vào `eval/results/input_gate.md`, kèm chi phí trung bình mỗi câu.
- **Nghiệm thu:** chặn nhầm câu `valid` ≤ 2% (đo lại); tỷ lệ lọt câu `off_topic` giảm so với chỉ tầng 0–1; chi phí tầng 2 mỗi lần gọi < 5% chi phí một run đầy đủ.
