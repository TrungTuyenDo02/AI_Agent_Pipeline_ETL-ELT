# ADR 0010 — Giám sát thay đổi cấu trúc nguồn (schema drift)

- Ngày: 2026-10-16 • Trạng thái: chấp nhận

## Bối cảnh

Danh mục nguồn chỉ là ảnh chụp lúc đăng ký. Đội backend có thể đổi kiểu, đổi tên, xóa cột mà không báo; sqlglot (V1) và sandbox (V2) đều chạy
trên ảnh cũ nên pipeline qua hết kiểm tra rồi hỏng hoặc cho số sai âm thầm ở production. Hệ thống không ngăn được backend đổi; chỉ có thể
phát hiện sớm, hỏng to và rõ, chỉ ra pipeline bị ảnh hưởng và đề xuất bản vá cho người duyệt.

## Quyết định

- **Mở rộng cái đang có** (chủ dự án chọn): giữ `schema_watch`/`schema_guard` (node Vs, bảng `schema_snapshots`) so cấu trúc lúc lập kế hoạch với
  lúc nạp trong MỘT run. Giai đoạn 5 thêm lớp theo NGUỒN và theo THỜI GIAN: bảng `source_schema_snapshots` (phiên bản, bản chuẩn),
  `schema_changes`, `profile_baselines`, `pipeline_dependencies` (migration 0006). Hai cơ chế không dẫm nhau: Vs chặn run đã sinh code khi bảng
  mất cột; G1 chặn từ đầu run khi nguồn lệch bản chuẩn.
- **Cấu trúc chuẩn hóa** qua `get_schema_fingerprint` (kiểu quy về `integer/decimal/float/string/boolean/date/timestamp/json/other`); luật phân loại
  nằm ở `config/drift_rules.yaml` (bảng "mở rộng an toàn": đổi kiểu chưa có trong bảng coi là `breaking`).
- **Khi nào kiểm:** G1 trước Planner (30 giây dùng lại kết quả cho nguồn vừa kiểm), kiểm lại ngay trước J2 (so với cấu trúc lúc run bắt đầu), nút
  "Kiểm tra lại cấu trúc", và định kỳ qua endpoint có khóa `DRIFT_CHECK_TOKEN`. Không có cơ sở dữ liệu ứng dụng (CLI demo) thì G1 bỏ qua.
- **Phản ứng:** chỉ hiển thị và trả qua API. Tuyệt đối không tự tạo run, tự chạy, tự merge: "Đề xuất bản vá" chỉ chạy khi người bấm và đi qua luồng chuẩn
  (sandbox, test, duyệt J2), vì đổi nghĩa dữ liệu (đồng → nghìn đồng) code không bắt chắc được.
- **Pipeline sinh ra tự phòng thủ (5.5):** `sources.yml` do code sinh từ hồ sơ dữ liệu (không phải LLM); macro `check_source_schema` chạy trước `dbt build`
  trong sandbox và là task đầu của DAG; V1 chặn `SELECT *` ở staging/mart, chặn DAG thiếu preflight ở đầu, chặn bộ test thiếu test ép kiểu bắt buộc.
- **Hợp đồng kiểu cột (model contract):** KHÔNG bật `contract: enforced` của dbt. Lý do: dbt-duckdb chưa ổn định với kiểu thập phân/thời gian, và hợp đồng
  buộc khai báo mọi cột bằng kiểu nguyên văn của adapter (dễ lệch với đặc tả). Thay bằng kiểm tra của V2 (`sandbox_run.type_mismatches`): kiểu
  cột bảng đích phải cùng nhóm kiểu chuẩn hóa với `output_columns` của đặc tả.

- **Hình trước/sau và đề xuất sửa pipeline:** `GET /schema-changes/{id}/diff` dựng từ hai phiên bản ảnh chụp; `POST /schema-changes/{id}/suggest` tìm file của pipeline đã sinh
  đọc bảng/cột bị đổi (sqlglot/regex trên SQL, `ref` cho mart) và ghép việc cần làm theo loại thay đổi bằng luật cố định. LLM (`drift_advice`, Gemini flash-lite)
  chỉ diễn giải thêm, chỉ khi người bấm, chỉ nhận cấu trúc; lỗi thì bỏ qua. Thêm ca `type_narrowed` (breaking) và `nullable_tightened` (info).

## Hệ quả

- Kịch bản "đổi đơn vị ×1000" không đổi cấu trúc nên chỉ cảnh báo thống kê; cần người phán đoán (ghi trong README, mục hạn chế).
- Đo bằng `scripts/simulate_drift.py` (kết quả ở `eval/results/drift.md`): mô phỏng trên sandbox, không phải trên cơ sở dữ liệu production.
- Nguồn CSDL ngoài chỉ đo hồ sơ thống kê khi kiểm định kỳ/nút kiểm tra (không đo trước mỗi run) để G1 nhanh và không tải thêm lên nguồn.
