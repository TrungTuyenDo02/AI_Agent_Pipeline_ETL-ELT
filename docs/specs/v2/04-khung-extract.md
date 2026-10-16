> Đọc `docs/specs/v2/00-chung.md` (quy tắc chung) trước khi làm giai đoạn này.

## 4. Giai đoạn 4 — Khung Extract chung với 3 bộ nạp

**Mục tiêu:** tách "lấy dữ liệu" khỏi lõi agent; thêm một nguồn database thật chỉ đọc.

### 4.1 Giao diện chung

Tạo `src/services/connectors/base.py` với lớp trừu tượng `SourceConnector`. Hai nhóm hàm tương ứng hai đường dữ liệu:

**Nhóm cho LLM (chỉ trả thứ đã được phép, đi qua `build_llm_context`):**
- `list_tables() -> list[str]`
- `get_schema(table) -> TableSchema` (cột, kiểu, khóa — dùng lại cấu trúc hiện có)
- `get_schema_fingerprint(tables=None) -> SchemaFingerprint` — cấu trúc chuẩn hóa (kiểu quy về tập nhỏ: `integer, decimal, float, string, boolean, date, timestamp, json, other`) kèm mã băm; dùng cho giai đoạn 5.
- `get_profile(table) -> TableProfile` — thống kê và dạng giá trị theo mục 3.3, **không chứa giá trị thật**; cột nhạy cảm bỏ min/max.
- `sample(table, n)` — **chỉ** hoạt động khi `llm_access == masked_sample`, ngược lại ném lỗi; luôn che bằng `pii.py`.

**Nhóm cho code (không trả dữ liệu về phía LLM):**
- `load_to_sandbox(tables, sandbox_conn, max_rows)` — nạp một tập con có hạt giống cố định vào DuckDB sandbox (`SANDBOX_LOAD_MAX_ROWS`). Cột nhạy cảm được thay bằng **giá trị băm có muối, nhất quán giữa các bảng** để JOIN vẫn đúng. Hàm không trả dòng dữ liệu cho nơi gọi.
- `health_check()` — kiểm tra kết nối, trả lỗi tiếng Việt thân thiện (đã qua `scrub_error`).

Mỗi connector chỉ nhận `DataSource` đã được lọc quyền (giai đoạn 3), không tự truy cập sổ.

**Làm rõ trong README (đoạn "Dữ liệu đi đâu"):** (1) dữ liệu thật chỉ được code đọc để nạp sandbox, đã che cột nhạy cảm; (2) LLM chỉ thấy cấu trúc/thống kê/mẫu đã che theo mức của nguồn; (3) khi công ty chạy pipeline thật trên hệ thống của họ, bước Extract do pipeline đã duyệt thực hiện bằng tài khoản của chính họ, ngoài hệ thống này.

### 4.2 Ba bộ nạp

1. `FileConnector` (CSV/JSON/SQLite): **chuyển logic hiện có** (`E0 Nhận nguồn`) vào khung chung, giữ nguyên hành vi.
2. `DuckDBConnector`: gói lại phần đã có.
3. `PostgresConnector` (mới): kết nối chỉ đọc (đặt `default_transaction_read_only=on` hoặc `SET TRANSACTION READ ONLY`), từ chối mọi câu lệnh không phải `SELECT` (kiểm tra bằng sqlglot trước khi chạy), có timeout, giới hạn số dòng, chỉ truy cập bảng trong `allowed_tables`. Bản thử: thêm service Postgres vào `docker-compose.yml` (profile riêng `dev-sources`, **không** bật mặc định), kèm script seed dùng bộ dữ liệu `P113 Retail` và một tài khoản chỉ có quyền `SELECT`.

### 4.3 Nối vào luồng

- Node `ingest` và `profile` (E0, P) gọi connector qua giao diện chung thay vì đọc file trực tiếp.
- Planner nhận thêm thông tin **loại nguồn** để đề xuất lựa chọn (xem 4.4).
- Thêm biến `CONNECTOR_TIMEOUT_SEC`, `SANDBOX_LOAD_MAX_ROWS`, `LLM_SAMPLE_MAX_ROWS` vào `.env.example`.

### 4.4 Lựa chọn pipeline do agent đề xuất

Mở rộng đặc tả (`src/models/spec.py`) và màn **Duyệt kế hoạch (J1b)** để Planner trình bày kèm lý do bằng lời thường, người dùng chọn hoặc chấp nhận mặc định:
- ETL hay ELT (giữ luật cố định hiện có, giải thích rõ hơn).
- Nạp toàn bộ hay nạp phần mới (incremental): gợi ý theo số dòng và có cột thời gian hay không.
- Lịch chạy: hằng ngày / hằng giờ / theo sự kiện (chỉ ghi vào DAG, không cần chạy thật).
- Loại nguồn và cách kết nối (lấy từ sổ đăng ký).

Các lựa chọn này là **dữ liệu có cấu trúc** trong spec để Coder và V0 (soát spec) dùng, không chỉ là văn bản.

### 4.5 Kiểm thử và nghiệm thu

- `tests/test_connectors.py`: chạy chung một bộ test hợp đồng cho cả 3 connector (cùng giao diện, cùng kết quả mong đợi). Thêm test: `sample()` ném lỗi khi mức không phải `masked_sample`; `get_profile()` không chứa giá trị thật của cột nhạy cảm; `load_to_sandbox` băm nhất quán (JOIN giữa hai bảng vẫn khớp sau khi băm).
- Test Postgres chỉ chạy khi có biến `RUN_PG_TESTS=1` (CI mặc định bỏ qua; ghi cách chạy vào RUNBOOK). Test bắt buộc: câu lệnh `INSERT/UPDATE/DELETE/DROP` bị từ chối **trước khi** tới database; bảng ngoài `allowed_tables` bị từ chối.
- **Nghiệm thu:** 12 ca golden và kịch bản "gộp 3 nguồn, doanh thu ngày" cho kết quả **không đổi** so với trước khi tách (chạy lại `make eval` phần kiểm chứng bằng code); luồng demo chạy qua `FileConnector` như cũ; có một ca demo chạy qua `PostgresConnector`.
