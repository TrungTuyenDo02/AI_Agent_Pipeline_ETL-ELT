-- Khởi tạo PostgreSQL trên Neon cho P-113 (dev / test / demo — CHỈ tài khoản thử, xem docs/NEON.md).
-- Cùng mô hình với scripts/postgres-init.sql (bản Docker):
--   p113_migrator: tạo/đổi cấu trúc bảng — CHỈ dùng khi chạy Alembic.
--   p113_app     : tài khoản ứng dụng; quyền trên từng bảng do migration cấp (GRANT trong migrations/versions).
-- Tạo role bằng SQL (không tạo trên Console): role tạo trên Console tự thuộc neon_superuser, quá rộng cho ứng dụng.
--
-- Chạy trên branch `main`, TRƯỚC khi tạo branch `dev` (branch con chép role, mật khẩu và database từ branch cha).
-- Mật khẩu: mỗi role một chuỗi ngẫu nhiên (Neon đòi ≥ 60 bit), tạo bằng
--   python -c "import secrets; print(secrets.token_urlsafe(24))"
-- rồi thay <MAT_KHAU_...> NGAY TRONG SQL Editor. Không lưu mật khẩu thật vào file này, không dán vào chat.

-- ===== Phần 1: SQL Editor chọn database `neondb` =====
CREATE ROLE p113_migrator LOGIN PASSWORD '<MAT_KHAU_MIGRATOR>' NOSUPERUSER NOCREATEROLE NOCREATEDB;
CREATE ROLE p113_app LOGIN PASSWORD '<MAT_KHAU_APP>' NOSUPERUSER NOCREATEROLE NOCREATEDB NOINHERIT;

-- ===== Phần 2: tạo 2 database bằng Console (Branch main → Databases → New database), owner `neondb_owner` =====
--   p113       : dữ liệu dev (branch dev) và demo (branch main)
--   p113_test  : chỉ cho pytest (tên phải chứa "test", tests/conftest.py kiểm tra)
-- (CREATE DATABASE không chạy được chung với lệnh khác trong SQL Editor nên làm bằng Console cho chắc.)

-- ===== Phần 3: SQL Editor chọn database `neondb` (quyền vào database) =====
-- Chỉ 2 role của app và nhóm quản trị Neon (Console, SQL Editor, MCP) được kết nối.
REVOKE ALL ON DATABASE p113 FROM PUBLIC;
REVOKE ALL ON DATABASE p113_test FROM PUBLIC;
GRANT CONNECT ON DATABASE p113 TO p113_migrator, p113_app, neon_superuser;
GRANT CONNECT ON DATABASE p113_test TO p113_migrator, p113_app, neon_superuser;

-- ===== Phần 4: SQL Editor chọn database `p113`, chạy; rồi chọn `p113_test`, chạy lại y hệt =====
-- PostgreSQL 15+: schema public chỉ cho PUBLIC quyền USAGE. Migrator được tạo bảng; ứng dụng chỉ được dùng schema.
GRANT USAGE, CREATE ON SCHEMA public TO p113_migrator;
GRANT USAGE ON SCHEMA public TO p113_app;

-- Kiểm tra (kỳ vọng: 2 dòng, rolsuper = false, không thuộc neon_superuser):
SELECT r.rolname, r.rolsuper, pg_has_role(r.rolname, 'neon_superuser', 'MEMBER') AS la_neon_superuser
FROM pg_roles r
WHERE r.rolname IN ('p113_migrator', 'p113_app');
