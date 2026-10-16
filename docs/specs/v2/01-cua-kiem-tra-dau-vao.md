> Đọc `docs/specs/v2/00-chung.md` (quy tắc chung) trước khi làm giai đoạn này.

## 1. Giai đoạn 1 — Cửa kiểm tra đầu vào, tầng 0 và 1 (0 token)

**Mục tiêu:** yêu cầu vô nghĩa hoặc lạc đề bị chặn **trước khi** vào planner; không tốn token, không hỏi làm rõ vô ích.

### 1.1 Vị trí

- Tạo `src/agents/nodes/input_gate.py` và đưa vào `graph.py` như node **đầu tiên**, đứng trước Planner.
- Hàm kiểm tra thuần (không gọi LLM) đặt ở `src/agents/tools/input_checks.py` để test riêng dễ.
- Thêm điều kiện rẽ nhánh trong `routing.py`: `rejected` → kết thúc luồng; `needs_info` → hỏi bằng mẫu cố định; `ok` → Planner.

### 1.2 Tầng 0 — luật cố định

Chặn (kèm mã lý do) khi:
- rỗng hoặc chỉ khoảng trắng; ngắn hơn `INPUT_MIN_CHARS` (mặc định 10);
- dài hơn `INPUT_MAX_CHARS` (mặc định 2000);
- tỷ lệ ký tự chữ/số quá thấp, hoặc một ký tự/cụm lặp lại bất thường (kiểu "asdfgh", "aaaaaa", "????");
- chứa mẫu tấn công prompt đơn giản (ví dụ: "bỏ qua hướng dẫn trước", "ignore previous instructions", "system prompt", yêu cầu in ra khóa/biến môi trường). Danh sách mẫu để trong file cấu hình riêng, dễ cập nhật. Đây chỉ là lớp chặn cơ bản.

### 1.3 Tầng 1 — đối chiếu danh mục nghiệp vụ

- Dựng một **bộ từ khóa nghiệp vụ** từ: tên bảng, tên cột trong danh mục (`src/services/source_catalog.py`, `src/services/catalog.py`), và từ điển nghiệp vụ (giai đoạn 6, tạm để rỗng).
- Chuẩn hóa tiếng Việt khi so khớp: bỏ dấu, chữ thường, bỏ ký tự thừa. Có bảng đồng nghĩa nhỏ (đơn hàng/order/đơn, doanh thu/revenue, khách hàng/customer...).
- Quy tắc: tìm thấy **ít nhất 1** từ khóa nghiệp vụ **hoặc** 1 động từ nghiệp vụ (gộp, tính, tổng hợp, báo cáo, tối ưu, nối, lọc...) thì cho qua. Không tìm thấy gì → trạng thái `unclear` (chuyển sang tầng 2 ở giai đoạn 2; trong giai đoạn 1 tạm coi là `rejected` kèm gợi ý viết lại).

### 1.4 Thông điệp trả về

- Từ chối **lịch sự**, tiếng Việt, kèm 2–3 ví dụ yêu cầu hợp lệ lấy từ danh mục thật (ví dụ: "Gộp dữ liệu đơn hàng 3 nguồn, tính doanh thu ngày").
- Trả về qua API đúng cấu trúc lỗi hiện có (`detail` tiếng Việt), mã trạng thái phù hợp; trong CLI hiển thị bằng `rich`.
- Không tạo run tốn tài nguyên khi bị chặn; nếu vẫn lưu, đánh dấu trạng thái `rejected_input` và **không tính vào hạn mức**.

### 1.5 Trần chi phí toàn hệ thống (làm luôn ở giai đoạn này)

Thêm vào `.env.example` và `src/services/` (đọc cấu hình tại một chỗ):
- `MAX_CLARIFY_ROUNDS=2` — tối đa 2 vòng hỏi làm rõ mỗi run; quá số vòng thì dừng và chuyển cho người (cứu hộ).
- `RUN_TOKEN_BUDGET` — trần token mỗi run; vượt thì dừng, báo rõ, không âm thầm tiếp tục.
- `USER_DAILY_RUN_LIMIT` — số run tối đa mỗi người mỗi ngày.
- Bộ nhớ đệm (cache) kết quả kiểm tra cho câu giống hệt nhau (chuẩn hóa rồi băm).

### 1.6 Kiểm thử bắt buộc

- `tests/test_input_gate.py`: mỗi luật tầng 0 có test riêng; tầng 1 có test khớp / không khớp / có dấu / không dấu.
- Bộ **50 câu mẫu** trong `eval/input_gate_cases.jsonl` (nhãn: `nonsense`, `off_topic`, `attack`, `valid`, `ambiguous`; tối thiểu 10 câu mỗi loại, các câu `valid` lấy từ 12 ca golden hiện có). Script `eval/run_input_gate.py` in ra: tỷ lệ **chặn nhầm câu hợp lệ**, tỷ lệ **lọt câu vô nghĩa/lạc đề**, ghi kết quả vào `eval/results/input_gate.md`.
- **Tiêu chí nghiệm thu giai đoạn 1:** chặn nhầm câu `valid` ≤ 2%; 100% câu `nonsense` và `attack` bị chặn mà **không gọi LLM**; toàn bộ test cũ vẫn xanh.
