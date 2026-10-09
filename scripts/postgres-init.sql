-- Khởi tạo PostgreSQL cục bộ (docker compose chạy file này MỘT lần khi volume còn trống).
-- Tạo 2 tài khoản kết nối + 2 cơ sở dữ liệu riêng cho dev và test (test không bao giờ dùng dữ liệu dev/prod):
--   p113_migrator: chủ sở hữu cơ sở dữ liệu, đổi cấu trúc bảng — CHỈ dùng khi chạy Alembic.
--   p113_app     : tài khoản ứng dụng, không phải superuser; quyền trên từng bảng do migration cấp.
-- Mật khẩu lấy từ biến môi trường của container (đặt trong .env), không ghi trong file này.

\getenv migrator_pw P113_MIGRATOR_PASSWORD
\getenv app_pw P113_APP_PASSWORD

CREATE ROLE p113_migrator LOGIN PASSWORD :'migrator_pw' NOSUPERUSER NOCREATEROLE NOCREATEDB;
CREATE ROLE p113_app LOGIN PASSWORD :'app_pw' NOSUPERUSER NOCREATEROLE NOCREATEDB NOINHERIT;

CREATE DATABASE p113_dev OWNER p113_migrator;
CREATE DATABASE p113_test OWNER p113_migrator;
REVOKE ALL ON DATABASE p113_dev FROM PUBLIC;
REVOKE ALL ON DATABASE p113_test FROM PUBLIC;
GRANT CONNECT ON DATABASE p113_dev TO p113_app;
GRANT CONNECT ON DATABASE p113_test TO p113_app;

\connect p113_dev
ALTER SCHEMA public OWNER TO p113_migrator;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO p113_app;

\connect p113_test
ALTER SCHEMA public OWNER TO p113_migrator;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO p113_app;
