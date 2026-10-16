> Đọc `docs/specs/v2/00-chung.md` (quy tắc chung) trước khi làm giai đoạn này.

## 5. Giai đoạn 5 — Phát hiện thay đổi cấu trúc nguồn (schema drift)

**Bối cảnh:** đội backend có thể đổi kiểu dữ liệu, đổi tên cột, xóa cột mà không báo. Danh mục hiện tại chỉ là "ảnh chụp" lúc đăng ký; sqlglot kiểm tên bảng/cột theo ảnh đó, và sandbox chạy trên dữ liệu cũng là ảnh cũ. Kết quả: pipeline qua hết kiểm tra nhưng **hỏng hoặc cho số sai âm thầm trên production**.

**Giới hạn phải nói thật:** không thể ngăn backend đổi mà không báo. Hệ thống chỉ có thể (1) **phát hiện sớm**, (2) **hỏng to và rõ thay vì sai lặng lẽ**, (3) **chỉ ra pipeline nào bị ảnh hưởng và đề xuất bản vá cho người duyệt**. Việc thỏa thuận hợp đồng dữ liệu giữa các đội là việc của tổ chức, ghi rõ trong README.

*Phụ thuộc:* cần xong giai đoạn 3 (sổ nguồn) và 4 (`get_schema_fingerprint`).

### 5.1 Mô hình dữ liệu

- `SchemaSnapshot`: `id`, `source_id`, `table`, `version` (số nguyên tăng dần), `columns` (tên, kiểu chuẩn hóa, cho phép rỗng, vị trí), `fingerprint`, `captured_at`, `is_baseline`.
- `SchemaChange`: `id`, `source_id`, `table`, `from_version`, `to_version`, `change_type`, `severity`, `detail`, `detected_at`, `status` ∈ {`open`, `acknowledged`, `resolved`}, `acknowledged_by`.
- `ProfileBaseline`: thống kê cơ sở theo cột (số dòng, % rỗng, số giá trị khác nhau, phân bố dạng giá trị, khoảng min/max cho cột không nhạy cảm) — lấy từ `get_profile` khi đặt baseline.
- `PipelineDependency`: `run_id` → danh sách (nguồn, bảng, cột) mà pipeline dùng. Tạo bằng cách phân tích SQL (sqlglot) và tận dụng lineage hiện có.

### 5.2 Phát hiện và phân loại

`src/services/schema_drift.py`: `capture_snapshot(source)`, `diff(old, new) -> list[SchemaChange]`.

| Thay đổi | Mức độ |
|---|---|
| Thêm cột | `info` |
| Đổi kiểu theo hướng mở rộng an toàn (ví dụ `integer`→`decimal`, `string` ngắn→dài) | `warning` |
| Đổi kiểu không tương thích (ví dụ `string`→`integer`, `decimal`→`string`, `timestamp`→`date`) | `breaking` |
| Xóa cột | `breaking` nếu có `PipelineDependency` dùng cột đó, ngược lại `warning` |
| Đổi cho phép rỗng (NOT NULL → NULL) | `warning` |
| Xóa bảng | `breaking` |
| Nghi đổi tên cột (xóa một cột và thêm một cột cùng kiểu, cùng vị trí hoặc tên gần giống trong cùng bảng) | `breaking` + gợi ý `possible_rename` cho người xác nhận |

Danh sách "mở rộng an toàn" để trong một bảng cấu hình, dễ chỉnh. Mọi thay đổi kiểu chưa có trong bảng coi là `breaking`.

### 5.3 Khi nào kiểm tra

- **Trước mỗi run** (sau cửa kiểm tra, trước Planner): so cấu trúc hiện tại của các nguồn liên quan với baseline. Có thay đổi `breaking` đang `open` → **chặn run**, nêu rõ bằng tiếng Việt thay đổi gì, ở bảng/cột nào. `admin` hoặc `engineer` có thể bấm "Tôi đã biết, dùng cấu trúc mới" để đặt baseline mới (ghi `AuditLog`). Mức `warning` và `info` cho chạy tiếp nhưng hiện cảnh báo ở màn Duyệt kế hoạch (J1b).
- **Ngay trước khi Reviewer duyệt (J2):** kiểm tra lại lần nữa, vì từ lúc sinh code đến lúc duyệt cấu trúc có thể đã đổi. Có `breaking` mới → hiện cảnh báo đỏ ở màn duyệt, chặn nút duyệt cho tới khi chạy lại sandbox.
- **Nút "Kiểm tra lại cấu trúc"** ở trang "Nguồn dữ liệu" (chỉ `admin`/`engineer` của phòng ban đó).
- **Định kỳ:** endpoint `POST /api/v1/sources/check-drift`, bảo vệ bằng khóa nội bộ `DRIFT_CHECK_TOKEN` (không đặt trong repo). Thêm workflow `.github/workflows/drift-check.yml` chạy theo lịch (mặc định hằng ngày) gọi endpoint này; có thể thay bằng bộ lập lịch khác. Mỗi lần chạy ghi `SchemaChange` nếu có thay đổi.

### 5.4 Phản ứng khi phát hiện thay đổi

- Trang "Thay đổi cấu trúc": danh sách thay đổi, mức độ, bảng/cột, pipeline bị ảnh hưởng (lấy từ `PipelineDependency`), trạng thái.
- Nút **"Đề xuất bản vá"** trên một pipeline bị ảnh hưởng: tạo **run mới** với ngữ cảnh gồm đặc tả cũ + danh sách `SchemaChange` (chỉ cấu trúc, không có dữ liệu), rồi đi qua **luồng chuẩn**: sandbox → test → duyệt J2. 
- **Tuyệt đối không** tự tạo run, tự chạy, tự merge khi phát hiện thay đổi. Chỉ người bấm nút mới tạo bản vá. Lý do: đổi nghĩa dữ liệu (ví dụ cột tiền đổi từ đồng sang nghìn đồng) code không bắt chắc được, cần người phán đoán (J).
- Chỉ hiển thị trong web và trả qua API; thông báo email/webhook để sau.

### 5.5 Pipeline sinh ra phải tự phòng thủ

Sửa prompt và kiểm tra của Coder / Test-gen / V1 để mọi pipeline mới có:
- **Khai báo nguồn dbt** (`sources.yml`): bảng, cột kỳ vọng, test `not_null`, `unique` ở khóa, `accepted_values` khi hợp lý, `freshness` khi có cột thời gian.
- **Kiểm tra cấu trúc nguồn lúc chạy (preflight):** một macro dbt `check_source_schema` so cột và kiểu thật (từ `information_schema`) với cột kỳ vọng trong `sources.yml`, **fail sớm** với thông báo rõ nếu lệch. DAG Airflow sinh ra có task đầu tiên gọi macro này trước mọi task biến đổi.
- **Không dùng `SELECT *`** ở staging và mart (chỉ cho phép ở lớp raw); chọn cột tường minh để cột mới không vô tình lọt vào mart, cột bị xóa làm hỏng to thay vì sai lặng lẽ. Thêm luật này vào kiểm tra sqlglot (V1).
- **Ép kiểu an toàn** ở staging (`try_cast` hoặc tương đương) và đếm số dòng không ép được; nếu tỷ lệ vượt `CAST_FAIL_THRESHOLD` (mặc định 1%) thì test fail, không âm thầm biến thành rỗng.
- **Giữ lớp raw nguyên bản** khi chọn ELT, để chạy lại được sau khi vá.
- **Hợp đồng kiểu cột của mô hình dbt (model contract):** bật nếu adapter dbt-duckdb đang dùng hỗ trợ. Thử nhanh trên một mô hình mẫu trước; nếu không hỗ trợ ổn định thì dùng test kiểu cột thay thế và ghi lại quyết định vào `docs/adr/`.

### 5.6 Thay đổi thống kê (nhẹ, chỉ cảnh báo)

Khi kiểm tra, so `get_profile` hiện tại với `ProfileBaseline`; chỉ phát cảnh báo `warning`, **không chặn**:
- % rỗng của cột tăng hơn `DRIFT_NULL_PCT_DELTA` điểm phần trăm (mặc định 20);
- số dòng lệch hơn `DRIFT_ROWCOUNT_RATIO` lần so với baseline (mặc định 3 lần, cả tăng và giảm);
- xuất hiện dạng giá trị mới chiếm hơn 5%;
- khoảng giá trị cột số không nhạy cảm lệch mạnh: gợi ý "có thể đổi đơn vị".

### 5.7 Kiểm thử và nghiệm thu

- `scripts/simulate_drift.py` áp 6 kịch bản "backend đổi không báo" lên DuckDB/Postgres thử: (1) tiền từ chuỗi sang số, (2) đổi tên cột `order_date` → `ordered_at`, (3) xóa cột đang dùng, (4) thêm cột mới, (5) cột bỗng rỗng nhiều, (6) cột tiền đổi đơn vị ×1000.
- `tests/test_schema_drift.py`: phát hiện đúng loại và mức độ; `possible_rename` được gợi ý ở kịch bản 2; thêm cột không chặn run; `breaking` chặn run; sau khi xác nhận thì chạy tiếp; cảnh báo đỏ xuất hiện ở bước duyệt khi cấu trúc đổi sau lúc sinh code.
- `tests/test_defensive_pipeline.py`: với mỗi kịch bản, chạy lại **pipeline đã sinh** trong sandbox và khẳng định: hoặc **fail sớm có thông báo rõ**, hoặc vẫn đúng (khi thay đổi vô hại như thêm cột); **không bao giờ cho kết quả sai mà báo thành công**. Kịch bản 6 chỉ cần cảnh báo thống kê (5.6).
- Thêm vào bộ mutation test hiện có (11/12) các lỗi giả: "bỏ preflight", "dùng `SELECT *`", "bỏ kiểm tra ép kiểu"; bộ kiểm chứng phải bắt được.
- Ghi kết quả vào `eval/results/drift.md`: tỷ lệ kịch bản bị bắt, thời gian từ lúc đổi đến lúc phát hiện, số lần báo nhầm.
- **Nghiệm thu:** 5/6 kịch bản bị chặn hoặc fail sớm có thông báo rõ (kịch bản 6 được cảnh báo); 0 trường hợp "sai nhưng báo thành công"; toàn bộ test cũ xanh; golden 12 ca không đổi kết quả.
