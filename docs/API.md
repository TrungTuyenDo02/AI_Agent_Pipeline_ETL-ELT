# API

Swagger: <http://localhost:8000/docs> (tắt khi `APP_ENV=production`). Danh sách dưới đây lấy từ `app.openapi()` ngày 2026-10-10.
Tiền tố `/api/v1`, riêng `/health` không có tiền tố.

## Quy ước

- **Đăng nhập:** cookie phiên HttpOnly do `POST /auth/login` đặt. Chưa đăng nhập → `401`; sai vai trò → `403` (ghi `audit_log`).
  Ngoại lệ không cần đăng nhập: `/health`, `/auth/login`, `/auth/logout`.
- **Thao tác ghi** (POST/PATCH) phải kèm header `X-Requested-With` (chống giả mạo yêu cầu từ trang khác).
- **Chạy nền:** thao tác làm agent chạy tiếp trả `202` ngay, các lần chạy xếp hàng một luồng. Web hỏi `GET /runs/{id}` định kỳ.
- **Lỗi:** `detail` tiếng Việt, không lộ traceback. Lỗi kiểm tra đầu vào: `422`.
- **Vai trò:** `engineer` tạo yêu cầu, trả lời, duyệt kế hoạch, cứu hộ; `reviewer` duyệt/từ chối code và sổ lỗi; `admin` quản lý tài khoản.

## Danh sách endpoint

| Method | Path | Vai trò | Mô tả |
|---|---|---|---|
| GET | `/health` | không | `status`, `timestamp`, `version`, `database`, `llm_provider` |
| GET | `/api/v1/status` | đăng nhập | LLM đang dùng, có phải mô phỏng không |
| POST | `/api/v1/auth/login` | không | Đăng nhập (`username`, `password`), đặt cookie phiên; khóa tạm sau nhiều lần sai |
| POST | `/api/v1/auth/logout` | không | Thu hồi phiên, xóa cookie |
| GET | `/api/v1/auth/me` | đăng nhập | Người dùng của phiên hiện tại |
| GET | `/api/v1/admin/users` | admin | Mọi tài khoản |
| POST | `/api/v1/admin/users` | admin | Cấp tài khoản mới |
| PATCH | `/api/v1/admin/users/{user_id}` | admin | Đổi vai trò, khóa/mở, đặt lại mật khẩu (không tự khóa mình) |
| GET | `/api/v1/admin/audit` | admin | Nhật ký kiểm toán, mới nhất trước (`limit` ≤ 200) |
| GET | `/api/v1/runs` | đăng nhập | Danh sách lần chạy (`limit` 1–100) |
| GET | `/api/v1/sources` | đăng nhập | Nguồn dữ liệu bạn được phép dùng (phòng ban mình + được cấp thêm; Admin: tất cả). Kèm tên phòng ban, mức AI được xem bằng lời; `secret_ref` (chỉ là tên tham chiếu) chỉ Admin thấy |
| POST | `/api/v1/sources` | admin | Đăng ký nguồn (`kind` file/duckdb/postgres, `secret_ref`, `allowed_tables`, `sensitivity`, `llm_access`, `restricted_columns`). Mức AI vượt trần theo độ nhạy cảm → `422` |
| PATCH | `/api/v1/sources/{id}` | admin | Sửa nguồn; nâng độ nhạy cảm thì mức AI tự hạ về trần |
| GET/POST | `/api/v1/sources/{id}/grants` | admin | Xem / cấp thêm quyền xem cho một người hoặc một phòng ban |
| DELETE | `/api/v1/sources/grants/{grant_id}` | admin | Thu hồi quyền xem thêm |
| GET/POST | `/api/v1/departments` | admin | Xem / tạo phòng ban |
| GET | `/api/v1/glossary` | đăng nhập | Thuật ngữ bạn được dùng: dùng chung + của phòng ban mình (Admin: tất cả) |
| POST | `/api/v1/glossary` | admin | Thêm thuật ngữ (`term`, `synonyms`, `definition`, `maps_to`, `department_id` trống = dùng chung). Trùng tên → `422` |
| PATCH | `/api/v1/glossary/{id}` | admin | Sửa thuật ngữ (`department_id=0` = chuyển thành dùng chung). Agent chỉ đọc, không tự ghi |
| GET | `/api/v1/schema-changes` | đăng nhập | Thay đổi cấu trúc của nguồn bạn được thấy (lọc `status`, `severity`, `source_id`), kèm pipeline bị ảnh hưởng |
| POST | `/api/v1/schema-changes/{id}/acknowledge` | admin, engineer | "Tôi đã biết, dùng cấu trúc mới": cấu trúc hiện tại thành bản chuẩn (ghi AuditLog) |
| POST | `/api/v1/sources/{id}/check-drift` | admin, engineer | Nút "Kiểm tra lại cấu trúc" của một nguồn; trả `DriftReport` (thay đổi mới, thay đổi chặn đang mở, cảnh báo) |
| POST | `/api/v1/sources/check-drift` | khóa nội bộ | Kiểm tra định kỳ mọi nguồn đang bật; header `X-Drift-Token` = `DRIFT_CHECK_TOKEN`. `503` nếu chưa cấu hình, `403` nếu sai khóa |
| POST | `/api/v1/runs/{run_id}/drift` | engineer | Cửa G1 chờ: `action` = `continue` (dùng cấu trúc mới làm bản chuẩn) hoặc `abort` |
| POST | `/api/v1/runs/{run_id}/patch` | engineer | "Đề xuất bản vá": tạo lần chạy MỚI từ đặc tả cũ + thay đổi cấu trúc đang mở (chỉ cấu trúc, không có dữ liệu); đi qua luồng chuẩn. `409` nếu không có thay đổi mở |
| POST | `/api/v1/runs` | engineer | Tạo yêu cầu (`request_text` tối đa 4000 ký tự) → `202` + `run_id`. Qua cửa kiểm tra đầu vào trước: rỗng, quá ngắn/dài, vô nghĩa, tấn công prompt hoặc lạc đề → `422` + `detail` tiếng Việt kèm ví dụ hợp lệ, không tạo lần chạy. Quá giới hạn lần chạy/ngày → `429` |
| GET | `/api/v1/runs/{run_id}` | đăng nhập | Trạng thái, câu hỏi đang chờ, tiến trình từng bước, đặc tả, bằng chứng, báo cáo tối ưu |
| GET | `/api/v1/runs/{run_id}/files` | đăng nhập | Code + test hiện tại và bản vòng trước (để xem diff) |
| GET | `/api/v1/runs/{run_id}/download` | đăng nhập | Gói `.zip` code dbt + test + DAG (không kèm dữ liệu sandbox) |
| POST | `/api/v1/runs/{run_id}/answers` | engineer | Trả lời câu hỏi làm rõ J1 (`answers`: id câu → lựa chọn nguyên văn) |
| POST | `/api/v1/runs/{run_id}/input` | engineer | Cửa kiểm tra đầu vào hỏi bổ sung / xin viết lại: `action` = `send` (kèm `text`) hoặc `abort` |
| POST | `/api/v1/runs/{run_id}/plan` | engineer | Duyệt kế hoạch J1b: `decision` = `approve` hoặc `revise` (kèm `note`) |
| POST | `/api/v1/runs/{run_id}/schema` | engineer | Nguồn mất cột/nghi đổi tên: `action` = `continue` (kèm `renames`) hoặc `abort` |
| POST | `/api/v1/runs/{run_id}/rescue` | engineer | Cứu hộ: `action` = `retry` (kèm `hint`) hoặc `abort` |
| POST | `/api/v1/runs/{run_id}/review` | reviewer | Duyệt J2: `decision` = `approve` hoặc `reject` (từ chối bắt buộc `note`) |
| GET | `/api/v1/runs/{run_id}/catalog` | đăng nhập | raw → staging → mart, kiểu cột, % rỗng, khóa, lineage, JOIN (0 token) |
| GET | `/api/v1/runs/{run_id}/profile` | engineer, reviewer | Hồ sơ dữ liệu một bảng (`table`, `dataset` = sandbox/small/dirty/dupkeys/nullmoney/few/empty) |
| GET | `/api/v1/reviews/queue` | đăng nhập | Các lần chạy chờ duyệt |
| GET | `/api/v1/errors` | đăng nhập | Mục sổ lỗi chờ duyệt |
| POST | `/api/v1/errors/{entry_id}/approve` | reviewer | Duyệt một mục sổ lỗi (kèm `fix`) |
| POST | `/api/v1/errors/{entry_id}/discard` | reviewer | Bỏ một mục |
| GET | `/api/v1/catalog/sources` | đăng nhập | Bảng nguồn nhóm theo hệ thống, số dòng, % rỗng, trùng khóa, gợi ý khóa nối |
| GET | `/api/v1/catalog/sources/profile` | engineer, reviewer | Hồ sơ dữ liệu một bảng nguồn (`table`), 50 dòng xem trước đã che PII |
| GET | `/api/v1/catalog/schema-changes` | đăng nhập | Cấu trúc file nguồn so với bản Reviewer đã duyệt |

## Thời gian phản hồi

p50/p95 của `/health`, danh sách lần chạy và đọc một lần chạy: [../eval/results/api_latency.md](../eval/results/api_latency.md)
(đo trong cùng tiến trình, chưa gồm độ trễ mạng).

## Cài tài khoản đầu tiên

Xem [DATABASE.md](DATABASE.md) mục 3: `python -m src.cli users create --username <tên> --role admin`.
