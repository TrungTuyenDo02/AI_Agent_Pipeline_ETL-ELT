# ADR 0007 — Sổ nguồn dữ liệu lưu cùng cơ sở dữ liệu tài khoản

- Ngày: 2026-10-15 • Trạng thái: chấp nhận

## Bối cảnh

CLAUDE.md bản 2 (mục 3.1) cần phòng ban, nguồn đã đăng ký, quyền xem thêm và nhật ký truy cập; yêu cầu "kiểm tra code hiện tại rồi
chọn Neon/Postgres hay SQLite, viết lớp truy cập tách riêng". Hiện trạng: tài khoản, phiên, `audit_log`, `schema_snapshots` đã nằm
ở cơ sở dữ liệu ứng dụng (PostgreSQL/Neon, SQLAlchemy 2, Alembic; test dùng SQLite tạm hoặc `TEST_DATABASE_URL`). Lần chạy, sổ lỗi,
bộ nhớ agent nằm ở kho trạng thái (`STATE_BACKEND`, SQLite hoặc Postgres).

## Quyết định

- Bảng mới `departments`, `data_sources`, `source_grants` và cột `users.department_id` nằm **cùng cơ sở dữ liệu tài khoản**, do
  Alembic quản lý (migration `0005_source_registry`, seed phòng "Mặc định" và nguồn "P113 Retail" để luồng demo cũ chạy).
  Lý do: quyền xem nguồn gắn với người dùng (khóa ngoại), cần truy vấn nối `users` và đổi đồng thời; tài khoản ứng dụng đã có quyền
  tối thiểu (`SELECT/INSERT/UPDATE` trên sổ nguồn, không đổi cấu trúc).
- Lớp truy cập tách riêng: `src/services/source_registry.py` (lớp ORM + hàm). **Cửa duy nhất** `get_visible_sources(user)`;
  `visible_catalog(user)` dựng danh mục bảng từ đó. `tests/test_source_registry.py` quét mã nguồn: ngoài danh sách cho phép, không
  module nào được đọc thư mục nguồn bằng `sources_dir` hay `discover_sources` trực tiếp.
- `AuditLog` dùng lại bảng `audit_log` hiện có (ai, khi nào, hành động, đích `source:<id>`, kết quả, chi tiết gồm `run_id`; không
  chứa dữ liệu nhạy cảm) thay vì tạo bảng thứ hai.
- Không có `DATABASE_URL` (CLI demo không cần PostgreSQL): sổ nguồn là một nguồn mặc định trong bộ nhớ, chỉ đọc.
- Tên người dùng do CLI khai (không có tài khoản) được coi thuộc phòng mặc định; API luôn dùng phiên đăng nhập thật. Đây là giới hạn
  đã biết của CLI chạy trên máy chủ (xem ARCHITECTURE: "CLI tin tham số `--as/--user`").
- Nguồn cấu hình thiếu bí mật (`secret_ref` chưa đặt ở máy chủ) bị bỏ qua kèm cảnh báo log, không làm hỏng danh sách của nguồn khác.

## Hệ quả

- Phải chạy `alembic upgrade head` trên cơ sở dữ liệu đang dùng (kể cả Neon) trước khi chạy bản mới.
- Mức truy cập mặc định của nguồn "P113 Retail" lấy `LLM_ACCESS_DEFAULT` tại thời điểm chạy migration; sau đó đổi bằng `PATCH /sources/{id}`.
