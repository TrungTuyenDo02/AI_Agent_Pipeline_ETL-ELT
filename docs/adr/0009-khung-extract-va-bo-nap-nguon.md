# ADR 0009 — Khung Extract chung và ba bộ nạp nguồn

- Ngày: 2026-10-15 • Trạng thái: chấp nhận

## Bối cảnh

Lõi agent đọc thẳng file trong thư mục nguồn. CLAUDE.md bản 2 (giai đoạn 4) yêu cầu tách "lấy dữ liệu" khỏi lõi agent, thêm một
nguồn cơ sở dữ liệu thật chỉ đọc, và giữ hai đường dữ liệu tách bạch: cho code (nạp sandbox) và cho LLM (qua `build_llm_context`).

## Quyết định

- `SourceConnector` (`src/services/connectors/base.py`) với hai nhóm hàm. Cho LLM: `list_tables`, `get_schema`, `get_schema_fingerprint`
  (kiểu chuẩn hóa về `integer/decimal/float/string/boolean/date/timestamp/json/other` + mã băm, dùng cho giai đoạn 5), `get_profile`,
  `sample` (ném lỗi nếu nguồn không ở mức `masked_sample`, luôn che). Cho code: `load_to_sandbox` (chỉ trả số dòng), `health_check`.
  Connector chỉ nhận `DataSource` đã lọc quyền và chỉ thấy bảng trong `allowed_tables`; bảng ngoài danh sách và bảng không tồn tại
  nhận cùng một thông báo.
- Ba bộ nạp: `FileConnector` (logic E0 cũ; kết quả nạp trùng khít `ingest_sources` cũ, có test), `DuckDBConnector` (mở chỉ đọc,
  nạp bằng ATTACH chỉ đọc), `PostgresConnector`.
- **PostgreSQL chỉ đọc nhiều lớp:** (1) mọi câu lệnh qua `check_select` (sqlglot, cú pháp PostgreSQL) TRƯỚC khi tới cơ sở dữ liệu: đúng
  một câu SELECT, không `SELECT INTO`/`FOR UPDATE`, không hàm ghi/ngủ/đọc file, mọi bảng phải trong `allowed_tables`; (2) mỗi giao dịch
  `BEGIN READ ONLY` (kể cả tài khoản có quyền ghi cũng không ghi được; có test với tài khoản quyền cao); (3) `statement_timeout`
  theo `CONNECTOR_TIMEOUT_SEC`, giới hạn số dòng. Không dùng tham số khởi động `options` để chạy được sau bộ gom kết nối (Neon pooler).
- **Nạp sandbox:** `SANDBOX_LOAD_MAX_ROWS` dòng mỗi bảng, tập con có hạt giống cố định (DuckDB `reservoir ... REPEATABLE`, PostgreSQL
  `TABLESAMPLE BERNOULLI ... REPEATABLE` rồi `LIMIT`). Cột nhạy cảm (tên gợi ý thông tin cá nhân hoặc admin đánh dấu) được thay bằng
  `h_<16 hex>` = SHA-256 có muối (`SANDBOX_HASH_SALT`), nhất quán giữa các bảng nên JOIN theo cột đó vẫn khớp.
- **Điều chỉnh so với CLAUDE.md:** băm cột nhạy cảm mặc định (`SANDBOX_HASH_SENSITIVE=auto`) chỉ áp cho nguồn độ nhạy cảm `high`, không
  áp mọi nguồn. Lý do: nghiệm thu yêu cầu golden 12 ca "không đổi kết quả" — ca g09 xuất cột `email` ra bảng đích, băm sẽ làm kết quả
  khác dữ liệu gốc; nguồn mặc định "P113 Retail" là `medium`. Muốn băm mọi nguồn: `SANDBOX_HASH_SENSITIVE=always`.
- Danh mục nguồn DB ghi `kind` = `duckdb`/`postgres` (đã thêm vào `TABULAR_KINDS`); J1 "giá trị thật của cột để người tick" chưa hỗ trợ
  nguồn DB (câu hỏi giữ lựa chọn của LLM).

## Hệ quả

- Nguồn lỗi (thiếu bí mật, không kết nối được) làm danh mục của riêng nó rỗng kèm cảnh báo log, không hỏng nguồn khác; ingest báo lỗi tiếng Việt đã che giá trị.
- Số dòng để chọn "nạp toàn bộ hay phần mới" do code đo qua `row_count` và không vào prompt.
- Kiểm thử PostgreSQL thật cần `RUN_PG_TESTS=1` (CI bỏ qua); phần kiểm tra chỉ đọc và bảng được phép chạy không cần máy chủ.
