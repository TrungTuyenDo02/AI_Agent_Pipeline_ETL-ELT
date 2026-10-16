> Đọc `docs/specs/v2/00-chung.md` (quy tắc chung) trước khi làm giai đoạn này.

## 3. Giai đoạn 3 — Sổ đăng ký nguồn, phân quyền phòng ban, mức truy cập dữ liệu của LLM

**Mục tiêu:** quản trị viên đăng ký nguồn; agent chỉ thấy nguồn đã đăng ký mà người dùng được phép, và chỉ thấy đúng mức dữ liệu cho phép.

### 3.1 Mô hình dữ liệu (Pydantic ở `src/models/`, lưu ở `src/services/store.py`)

Nếu dự án đã dùng Neon/Postgres cho tài khoản thì thêm bảng ở đó; nếu chưa thì dùng SQLite hiện có và **viết lớp truy cập tách riêng** để đổi sang Postgres sau không phải sửa chỗ khác. Kiểm tra code hiện tại rồi chọn, ghi quyết định vào `docs/adr/`.

- `Department`: `id`, `name`.
- `User`: thêm `department_id`, `role` ∈ {`admin`, `engineer`, `reviewer`} (nếu đã có vai trò thì **mở rộng**, không làm lại).
- `DataSource`: `id`, `name`, `department_id`, `kind` ∈ {`file`, `duckdb`, `postgres`}, `secret_ref` (chỉ là **tên tham chiếu**, tuyệt đối không chứa mật khẩu), `allowed_tables` (danh sách), `sensitivity` ∈ {`low`, `medium`, `high`}, **`llm_access` ∈ {`schema_only`, `profile`, `masked_sample`}** (mặc định lấy từ `LLM_ACCESS_DEFAULT`), `restricted_columns` (cột nhạy cảm admin đánh dấu thêm, ngoài cột `pii.py` tự nhận ra), `enabled`.
- `SourceGrant`: cấp thêm quyền xem nguồn của phòng ban khác cho một người/phòng ban (tùy chọn, làm tối giản).
- `AuditLog`: `who`, `when`, `action`, `source_id`, `run_id`, `result` (không chứa dữ liệu nhạy cảm).

### 3.2 Quy tắc truy cập

- Mặc định: người dùng chỉ thấy nguồn của **phòng ban mình**; `admin` thấy tất cả.
- Mọi đường vào dữ liệu (catalog, ingest, planner, API) phải đi qua **một hàm duy nhất** `get_visible_sources(user)` ở `src/services/source_registry.py`. Cấm truy cập nguồn bằng đường khác. Thêm test đảm bảo không có đường vòng.
- Planner, Coder, Test-gen, Optimizer chỉ nhận ngữ cảnh dữ liệu từ `build_llm_context` (mục 3.3). Yêu cầu nhắc tới bảng ngoài quyền → từ chối bằng thông điệp tiếng Việt rõ ràng (không tiết lộ bảng đó có tồn tại hay không).
- Vai trò: `admin` đăng ký/sửa nguồn và phòng ban; `engineer` tạo yêu cầu; `reviewer` duyệt. **Bật mặc định tách người tạo và người duyệt** (đổi `REQUIRE_SEPARATE_REVIEWER` mặc định thành `true`, cập nhật test và README; vẫn cho tắt khi chạy demo cá nhân).

### 3.3 Mức truy cập dữ liệu của LLM (`build_llm_context`)

**Lý do:** chỉ cho LLM xem cấu trúc bảng là quá chặt. Planner cần biết dữ liệu bẩn kiểu gì (trùng khóa, ngày lẫn định dạng, tiền có dấu chấm `1.075.000`, rỗng nhiều) mới sinh đúng phép làm sạch; 12 ca golden hiện có đúng là các loại này. Giải pháp: cho xem **thống kê và dạng giá trị**, không cho xem dòng thật.

Tạo `src/services/llm_context.py` với `build_llm_context(user, source_ids, tables) -> LLMContext`. Đây là **cửa duy nhất** tạo ngữ cảnh dữ liệu cho prompt. Ba mức:

| Mức | LLM được thấy | Không được thấy |
|---|---|---|
| `schema_only` | tên bảng, tên cột, kiểu, khóa, quan hệ | mọi thống kê, mọi giá trị |
| `profile` (mặc định) | + số dòng, % rỗng, số giá trị khác nhau, tỷ lệ trùng khóa, **dạng giá trị** và phân bố các dạng | giá trị thật |
| `masked_sample` | + tối đa `LLM_SAMPLE_MAX_ROWS` (mặc định 5) dòng đã che | dòng chưa che |

Quy tắc chi tiết:
- **Dạng giá trị (shape pattern):** chữ số → `9`, chữ cái → `a`, giữ dấu phân cách. Ví dụ `1.075.000` → `9.999.999`; `15/03/2026` → `99/99/9999`. Phân bố ví dụ: "92% `99/99/9999`, 8% `9999-99-99`". Chuỗi dài thì cắt gọn dạng.
- **Khoảng min/max** chỉ tính cho cột số/ngày **không** thuộc `restricted_columns` và không bị `pii.py` nhận là nhạy cảm. Cột nhạy cảm chỉ có số đếm và dạng giá trị, không có min/max, không có giá trị phổ biến nhất.
- **Không đưa danh sách giá trị phổ biến** (top values), trừ cột phân loại ít giá trị (≤ 10 giá trị khác nhau) thuộc nguồn `sensitivity=low` và không phải cột nhạy cảm.
- `masked_sample`: chỉ khi `sensitivity=low` **và** admin bật rõ ràng; mọi cột đi qua `pii.py`; số dòng ≤ trần.
- **Ràng buộc theo độ nhạy cảm:** `high` → ép `schema_only`; `medium` → tối đa `profile`; `low` → tối đa `masked_sample`. Kiểm tra ở API đăng ký (từ chối cấu hình sai) và kiểm tra lại trong `build_llm_context` (phòng thủ lần hai; vượt mức thì hạ xuống mức cho phép và ghi `AuditLog`).
- Biến `LLM_ACCESS_DEFAULT=profile` trong `.env.example`. **Ghi rõ trong README:** đây là điều chỉnh so với quyết định ban đầu "chỉ cho xem schema"; đặt `LLM_ACCESS_DEFAULT=schema_only` để quay về như cũ.
- Phải kiểm tra bước "Soi dữ liệu" (P) hiện có: nếu nó đã đưa thống kê vào prompt thì **chuyển vào `build_llm_context`**, không để hai đường song song.

### 3.4 Làm sạch thông báo lỗi (`scrub_error`)

- Tạo `src/agents/tools/scrub.py` với `scrub_error(text) -> str`: thay bằng `<đã che>` các chuỗi trong dấu nháy, email, số điện thoại, số dài, giá trị trong mẫu thông báo kiểu "Could not convert string '...'", "Conversion Error", Postgres `Key (cột)=(giá trị)`, và đường dẫn tuyệt đối có tên người dùng.
- Áp dụng ở **mọi** chỗ đưa lỗi vào prompt: vòng sửa lỗi (≤ 3 vòng), cứu hộ, optimizer. Gom về một hàm tạo prompt lỗi để không sót đường.
- Giữ bản lỗi gốc cho người dùng có quyền xem (hiển thị trên web), chỉ phiên bản đã che đi vào LLM.

### 3.5 Quản lý chìa khóa

- `secret_ref` được giải thành giá trị thật **chỉ ở lớp kết nối** (`src/services/connectors/`), từ biến môi trường hoặc kho bí mật. Giá trị thật không đi vào state, log, prompt, checkpoint, response API.
- Viết `src/services/secrets.py` với một hàm `resolve(secret_ref)`; nếu thiếu → lỗi rõ ràng bằng tiếng Việt, không in giá trị.

### 3.6 API và giao diện

- API (chỉ `admin`): `POST/GET/PATCH /api/v1/sources`, `POST/GET /api/v1/departments`; `GET /api/v1/sources` cho người thường chỉ trả nguồn được phép. Phản hồi **không bao giờ** chứa giá trị bí mật (chỉ tên tham chiếu).
- Trang web mới "Nguồn dữ liệu" (Next.js): danh sách nguồn, phòng ban, mức nhạy cảm, **mức truy cập của LLM** (hiển thị bằng lời dễ hiểu: "AI chỉ thấy cấu trúc" / "AI thấy thống kê, không thấy dòng thật" / "AI thấy vài dòng đã che"), bảng được phép; form đăng ký chỉ hiện cho `admin`. Giữ phong cách giao diện hiện tại, hỗ trợ sáng/tối.
- Nếu **đăng nhập chưa có** (phát hiện ở bước đọc code): dừng và báo lại cho người dùng, **không tự dựng hệ đăng nhập khác** mà chưa được đồng ý.

### 3.7 Kiểm thử và nghiệm thu

- `tests/test_source_registry.py`, `tests/test_permissions.py`: người phòng A không thấy nguồn phòng B; bảng ngoài `allowed_tables` bị từ chối; `admin` thấy tất cả; người tạo run không tự duyệt được khi bật tách vai trò; mọi truy cập được ghi `AuditLog`.
- `tests/test_llm_context.py`: với dữ liệu thử chứa chuỗi bí mật mẫu (email, số điện thoại, tên người, số tiền), khẳng định **không chuỗi nào xuất hiện trong ngữ cảnh** ở mức `schema_only` và `profile`; mức `masked_sample` chỉ chứa phiên bản đã che; nguồn `high` không thể nâng mức.
- `tests/test_scrub.py`: lỗi mẫu của DuckDB, dbt, Postgres chứa giá trị thật → sau `scrub_error` không còn giá trị; quét toàn bộ prompt trong một run thử, không có chuỗi bí mật mẫu.
- Test "không lộ bí mật": quét log/state/response giả lập, khẳng định không chứa chuỗi bí mật mẫu.
- **Nghiệm thu:** CI xanh; các test trên xanh; luồng demo cũ vẫn chạy với nguồn mặc định `P113 Retail` được đăng ký sẵn vào sổ (seed); chạy lại golden 12 ca với `LLM_ACCESS_DEFAULT=profile`, độ đúng **không thấp hơn** trước khi đổi (ghi vào `eval/results/llm_access.md`, so sánh `schema_only` và `profile`).
