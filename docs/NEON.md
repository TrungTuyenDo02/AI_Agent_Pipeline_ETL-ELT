# PostgreSQL trên Neon (dev, test, demo)

Neon là PostgreSQL chạy trên cloud. Dự án dùng Neon thay cho Postgres trong Docker ở **dev, test và bản demo**.
Mô hình giữ nguyên như bản Docker: hai tài khoản, quyền tối thiểu (xem [DATABASE.md](DATABASE.md)).

## 0. Phạm vi (quyết định 2026-10-13, xem [JOURNAL.md](../JOURNAL.md))

| Điều | Chốt |
|---|---|
| Vùng | Singapore `aws-ap-southeast-1` (Neon không có vùng Việt Nam) |
| Dữ liệu | **Chỉ tài khoản thử**, không dữ liệu nhân viên thật. Production thật vẫn đặt tại Việt Nam |
| Gói | Free: 1 GB/project, 100 CU-giờ/tháng, tự ngủ sau 5 phút, khôi phục trong 6 giờ |
| Branch | `main` = demo · `dev` = máy bạn + pytest (tạo từ `main` **sau** khi khởi tạo) |
| Quản trị | Neon Console / SQL Editor; Claude qua Neon MCP **chỉ đọc**, chỉ một project |

Chỉ có bảng đăng nhập, phiên, nhật ký kiểm toán và ảnh chụp cấu trúc nguồn nằm ở PostgreSQL.
Lịch sử lần chạy và checkpoint vẫn ở SQLite trong `data/`.

## 1. Tạo project *(bạn tự làm, cần tài khoản Neon)*

1. <https://console.neon.tech> → **New project**: tên `p113`, Postgres 17, vùng **AWS Asia Pacific (Singapore)**.
2. Ghi lại **Project ID** (Settings → General). ID không phải bí mật, dùng cho MCP ở mục 5.

## 2. Tạo tài khoản và database (branch `main`)

Làm theo từng phần trong [scripts/neon-init.sql](../scripts/neon-init.sql):

1. SQL Editor (database `neondb`): tạo `p113_migrator`, `p113_app`. Mật khẩu tạo bằng
   `python -c "import secrets; print(secrets.token_urlsafe(24))"`, thay thẳng trong SQL Editor.
2. Console → **Databases → New database**: `p113` và `p113_test`, owner `neondb_owner`.
3. SQL Editor (database `neondb`): quyền kết nối. Rồi chọn `p113`, chạy phần 4; chọn `p113_test`, chạy lại phần 4.
4. Câu kiểm tra cuối file trả 2 dòng, cột `rolsuper` và `la_neon_superuser` đều `false`.

Sau đó **Branches → New branch** `dev` từ `main`. Branch con chép role, mật khẩu và database của branch cha.

## 3. Chuỗi kết nối vào `.env`

**Connect** trên Console, chọn branch, database, role. Bật/tắt **Connection pooling** theo bảng. Đổi đầu chuỗi
`postgresql://` thành `postgresql+psycopg://`, phần đuôi dùng `?sslmode=verify-full&sslrootcert=system&connect_timeout=15`.

| Biến (`.env`) | Branch | Database | Role | Pooling |
|---|---|---|---|---|
| `DATABASE_URL` | `dev` | `p113` | `p113_app` | **bật** (host có `-pooler`) |
| `MIGRATION_DATABASE_URL` | `dev` | `p113` | `p113_migrator` | **tắt** (Neon: migration đi thẳng) |
| `TEST_DATABASE_URL` | `dev` | `p113_test` | `p113_migrator` | **tắt** |

- Tự dán vào `.env`, **không dán vào chat**. Bản demo (Render/Cloud Run) dùng chuỗi của branch `main`, nhập ở trang biến môi trường của dịch vụ.
- `connect_timeout=15`: compute đang ngủ cần vài giây để dậy ở lần kết nối đầu.
- Gặp lỗi chứng chỉ trên Windows thì tạm đổi `sslmode=verify-full&sslrootcert=system` thành `sslmode=require` (Neon luôn bắt buộc TLS).
- Có `TEST_DATABASE_URL` trong `.env` thì **mọi** lần chạy pytest đều dùng Neon (chậm hơn, tốn CU-giờ). Muốn quay về SQLite tạm thì xóa dòng đó.

## 4. Chạy migration và tạo tài khoản

```bash
alembic upgrade head                 # kỳ vọng: 0002_schema_snapshots (head), không lỗi
python -m src.cli users seed-dev     # chỉ tài khoản thử (an / binh / quantri), mật khẩu in MỘT lần
python -m src.cli doctor             # dòng "Cơ sở dữ liệu" phải ✓
```

Bản demo: chạy `alembic upgrade head` với `MIGRATION_DATABASE_URL` của branch `main`.

## 5. Claude quản trị bằng Neon MCP (chỉ đọc)

```bash
claude mcp add --transport http neon "https://mcp.neon.tech/mcp?readonly=true&projectId=<PROJECT_ID>"
```

Rồi gõ `/mcp` trong Claude Code, chọn `neon`, đăng nhập Neon (OAuth). `readonly=true` chỉ cho SELECT và xem cấu trúc.
`projectId` khóa vào đúng project này. Neon khuyên không nối MCP vào production hay dữ liệu cá nhân thật.

## 6. Vận hành

- **Làm sạch `dev`:** Branches → `dev` → **Reset from parent** (về đúng trạng thái `main`).
- **Sao lưu:** `pg_dump` qua chuỗi kết nối **không** pooling. Gói Free chỉ khôi phục được trong 6 giờ gần nhất.
- **Bản Docker:** vẫn dùng được khi không có mạng (`docker compose up -d db`, chuỗi `127.0.0.1:5433` như [DATABASE.md](DATABASE.md)).
