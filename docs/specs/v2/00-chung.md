# CLAUDE.md — Bổ sung (bản 2): Cửa kiểm tra đầu vào, Sổ nguồn, Mức truy cập dữ liệu, Khung Extract, Phát hiện thay đổi cấu trúc

> Dán nội dung này vào cuối `CLAUDE.md` hiện có (hoặc để thành file riêng và tham chiếu từ `CLAUDE.md`).
> Ngôn ngữ giao diện, thông báo lỗi, câu hỏi cho người dùng: **tiếng Việt**. Tên biến, hàm, file: tiếng Anh.
>
> **Thay đổi so với bản 1:**
> - Làm rõ "agent không xem dữ liệu" nghĩa là gì: tách **đường dữ liệu cho code** và **đường dữ liệu cho LLM**, thêm 3 mức truy cập (mục 0.5, 3.3).
> - Thêm bước **làm sạch thông báo lỗi** trước khi đưa vào prompt (0.5, 3.4).
> - Thêm **giai đoạn 5: phát hiện thay đổi cấu trúc (schema drift)**; giai đoạn từ điển nghiệp vụ cũ thành **giai đoạn 6**.

## 0. Quy tắc chung (đọc trước khi làm)

1. **Đọc đúng chỗ, sửa sau.** Không đọc cả danh sách thư mục. Với giai đoạn đang làm: dùng Grep tìm tên hàm/lớp liên quan, chỉ đọc những file giai đoạn đó thực sự chạm tới (điểm bắt đầu gợi ý: `graph.py`, `routing.py`, `state.py`, `tools/pii.py`, `services/source_catalog.py`, `services/store.py`). Việc rà rộng giao cho subagent Explore, chỉ nhận bản tóm tắt. Trước khi làm, tóm tắt ngắn những gì đã có (đặc biệt: **đăng nhập đã có chưa, ở file nào; bước "Soi dữ liệu" (P) hiện đưa gì vào prompt**). Không giả định.
2. **Làm theo giai đoạn (mục 1 → 6), mỗi giai đoạn xong phải qua `python scripts/tasks.py ci` (ruff + pytest, độ phủ ≥ 60%) mới sang giai đoạn sau.** Mỗi giai đoạn một commit riêng, thông điệp rõ ràng.
3. **Không phá vỡ cái đang chạy.** 280 test hiện có phải tiếp tục xanh. Chế độ `LLM_PROVIDER=mock` phải tiếp tục chạy trọn luồng mà không cần khóa API.
4. **Nguyên tắc J-E-V:** kiểm tra bằng code (0 token) làm trước, LLM chỉ gọi khi code không đủ kết luận. Mọi tính năng mới phải theo nguyên tắc này.
5. **Bảo mật bất biến (không được vi phạm, kể cả khi tiện):**
   - **Hai đường dữ liệu tách bạch.**
     - *Đường cho code:* code thuần (connector, sandbox, dbt, DuckDB) được đọc dữ liệu để nạp và chạy pipeline. Kết quả mẫu chỉ hiện cho người dùng có quyền xem nguồn đó.
     - *Đường cho LLM:* mọi thứ đi vào prompt phải đi qua **một hàm duy nhất** `build_llm_context(...)` (giai đoạn 3), tuân theo mức `llm_access` của nguồn. **LLM không bao giờ thấy dòng dữ liệu thật** (trừ mức `masked_sample`, và khi đó cũng đã che).
   - **Ba mức `llm_access`:** `schema_only` < `profile` (mặc định) < `masked_sample`. Chi tiết ở mục 3.3.
   - LLM **không bao giờ** nhìn thấy mật khẩu, khóa API, chuỗi kết nối. Chỉ thấy tên tham chiếu (ví dụ `conn_orders_db`).
   - **Thông báo lỗi từ dbt/DuckDB/Postgres có thể chứa giá trị dữ liệu thật** (ví dụ "không ép được chuỗi 'abc@x.com' sang số"). Mọi thông báo lỗi phải qua `scrub_error()` (mục 3.4) trước khi vào prompt: vòng sửa lỗi, cứu hộ, optimizer, mọi chỗ khác.
   - Kết nối nguồn dữ liệu chỉ dùng tài khoản **chỉ đọc**; code không được chạy câu lệnh ghi/xóa lên nguồn.
   - Không ghi khóa, token, mật khẩu, dữ liệu thật vào log, state LangGraph, checkpoint, `.ai-log`, hay dữ liệu gửi lên công cụ theo dõi (LangSmith). Chỉ prompt đã qua `build_llm_context` mới được ghi lại.
   - Sandbox vẫn chỉ DuckDB local; không chạy gì trên production.
6. **Ngoài phạm vi (KHÔNG làm trong đợt này):** API đối tác, OAuth, phân quyền theo từng dòng dữ liệu, theo dõi thay đổi dữ liệu (CDC), schema registry, Kafka, BigQuery, MCP, **tự động chạy hoặc tự merge bản vá khi phát hiện thay đổi cấu trúc**, thông báo qua email/webhook. Nếu cần, ghi vào mục "Hạn chế đã biết" của README.
7. **Cuối mỗi giai đoạn:** cập nhật `WORKLOG.md` (làm gì, vì sao, kết quả đo) và các mục liên quan trong `README.md`, `docs/RUNBOOK.md`, `.env.example`.
