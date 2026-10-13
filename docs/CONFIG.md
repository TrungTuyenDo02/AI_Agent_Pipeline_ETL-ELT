# Cấu hình (biến môi trường)

Giá trị mẫu: [.env.example](../.env.example). Chép thành `.env` (đã git-ignore) rồi sửa. Mặc định chạy được hoàn toàn bằng chế độ mô phỏng, không cần khóa.
Nguồn sự thật của mặc định: [src/config.py](../src/config.py). Cột **Bí mật** = có thì chỉ đặt trong `.env` hoặc dịch vụ quản lý bí mật, **không** commit, in ra hay ghi log.

## LLM

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `LLM_PROVIDER` | `mock` (câu trả lời cố định), `openai` (model thật theo `config/models.yaml`), `google` (Gemini mọi bước) | `mock` | không |
| `OPENAI_API_KEY` | Khóa OpenAI (bước nào khai báo `provider: openai`) | trống | **có** |
| `ANTHROPIC_API_KEY` | Khóa Anthropic (bước nào khai báo `provider: anthropic`, hiện là Optimizer) | trống | **có** |
| `GOOGLE_API_KEY` | Khóa Gemini (khi `google` hoặc làm dự phòng) | trống | **có** |
| `LLM_FALLBACK` | `google` = model chính gọi lỗi thì chuyển Gemini; `none` = tắt | `google` | không |
| `LLM_TEMPERATURE` | Chỉ Codegen dùng, tối đa 0,2; bước khác luôn 0 (Opus 5.5 không nhận temperature) | `0` | không |
| `LLM_MAX_TOKENS` | Trần token đầu ra chung (mỗi bước có trần riêng nhỏ hơn) | `16000` | không |
| `LLM_STRUCTURED_OUTPUT` | Gửi JSON Schema strict; `false` = quay về `json_object` | `true` | không |

**Tên model** không đặt bằng biến môi trường: chỉ khai báo trong [config/models.yaml](../config/models.yaml) (mỗi bước một dòng `provider` + `name`, Anthropic thêm `effort`; mục `fallback` là model Gemini). Hiện tại: Planner/Codegen/Testgen = `gpt-5.6-luna`, Optimizer = `claude-haiku-5-5` (không đặt effort), dự phòng = `gemini-3.1-flash-lite`. Các biến cũ `MODEL_NAME`, `MODEL_<BƯỚC>`, `GOOGLE_MODEL_NAME` không còn tác dụng.

## Đăng nhập và cơ sở dữ liệu

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL của **tài khoản ứng dụng** `p113_app`; production thêm `?sslmode=verify-full` | trống (tắt đăng nhập) | **có** |
| `MIGRATION_DATABASE_URL` | Chuỗi của tài khoản `p113_migrator`, chỉ dùng khi chạy `alembic` | trống | **có** |
| `TEST_DATABASE_URL` | Cơ sở dữ liệu riêng cho test (tên phải chứa `test`); trống = test dùng SQLite tạm | trống | **có** |
| `SESSION_SECRET` | Khóa ký phiên, ≥ 32 ký tự ngẫu nhiên (`python -c "import secrets; print(secrets.token_urlsafe(48))"`); đổi = mọi phiên mất hiệu lực | trống | **có** |
| `SESSION_TTL_MINUTES` | Thời hạn phiên (5–1440) | `480` | không |
| `SESSION_COOKIE_SECURE` | Cookie chỉ gửi qua HTTPS; chỉ tắt khi thử bằng http qua IP mạng nội bộ | `true` | không |
| `SESSION_COOKIE_SAMESITE` | `lax`, `strict`, `none` (khác tên miền cần `none` kèm Secure) | `lax` | không |
| `LOGIN_MAX_FAILURES` | Số lần sai trước khi khóa tạm | `5` | không |
| `LOGIN_LOCK_MINUTES` | Số phút khóa tạm | `15` | không |
| `FORCE_HTTPS` | `true` khi triển khai: chuyển hướng HTTP sang HTTPS | `false` | không |
| `POSTGRES_PASSWORD`, `P113_MIGRATOR_PASSWORD`, `P113_APP_PASSWORD` | Mật khẩu cho `docker compose` tạo PostgreSQL và hai tài khoản | trống | **có** |
| `P113_DB_PORT` | Cổng PostgreSQL của docker compose trên máy | `5433` | không |

## Ứng dụng

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `APP_ENV` | `development`, `production`, `test`. `production` tắt `/docs` và cấm tài khoản mẫu | `development` | không |
| `APP_HOST` / `APP_PORT` | Có trong cấu hình nhưng code hiện chưa dùng: cổng thật do lệnh `uvicorn --port` hoặc biến `PORT` quyết định | `0.0.0.0` / `8000` | không |
| `PORT` | Cổng cho container (Render/Railway/Cloud Run truyền vào); Dockerfile dùng `${PORT:-8000}` | `8000` | không |
| `CORS_ORIGINS` | Các địa chỉ web được gọi API, cách nhau bằng dấu phẩy | `http://localhost:3000` | không |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | không |
| `NEXT_PUBLIC_API_URL` | (Frontend) địa chỉ API nhìn từ trình duyệt; **nhúng vào bản build**, đặt trước khi build | `http://localhost:8000` | không |

## Lưu trữ

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `DATA_DIR` | Thư mục dữ liệu chung | `./data` | không |
| `SOURCES_DIR` | Kho nguồn giả lập | `./data/sources` | không |
| `STORE_PATH` | SQLite lần chạy, duyệt, sổ lỗi | `./data/app.db` | không |
| `CHECKPOINT_PATH` | SQLite checkpoint LangGraph | `./data/checkpoints.db` | không |
| `TEMPLATE_DIR` | Dự án dbt mẫu | `./pipelines/template` | không |
| `WORKSPACES_DIR` | Nơi sinh workspace từng lần chạy | `./pipelines/workspaces` | không |

## Sandbox và vòng lặp agent

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `SANDBOX_TIMEOUT_SEC` | Giới hạn thời gian `dbt build` (V2) | `300` | không |
| `SANDBOX_MEMORY_LIMIT` | Giới hạn bộ nhớ DuckDB | `1GB` | không |
| `SANDBOX_THREADS` | Số luồng DuckDB | `2` | không |
| `MAX_FIX_ATTEMPTS` | Số vòng sửa V1/V2 tối đa trước khi cứu hộ | `3` | không |
| `MAX_ACTIVE_RUNS_PER_USER` | Số lần chạy đang chờ/đang chạy cùng lúc của một người tạo yêu cầu; vượt → 429 | `2` | không |
| `LLM_DAILY_BUDGET_USD` | Trần chi phí LLM mỗi người mỗi ngày (giờ VN), tính từ `cost_usd` các lần chạy; `0` = không chặn | `1` | không |
| `MAX_PLAN_ROUNDS` | Số vòng lập kế hoạch/làm rõ tối đa | `5` | không |
| `MAX_REVIEW_ROUNDS` | Số lần yêu cầu sửa kế hoạch tối đa | `3` | không |
| `SEED` | Hạt giống dữ liệu thử | `42` | không |
| `MOCK_SMALL_ROWS` / `MOCK_LARGE_ROWS` | Số dòng bộ dữ liệu `small` / `large` | `200` / `300000` | không |

## Optimizer và đối chiếu

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `OPT_MIN_GAIN_PCT` | Chỉ áp dụng khi nhanh hơn ít nhất ngưỡng này (%) | `15` | không |
| `OPT_RUNS_PER_MONTH` | Số lần chạy mỗi tháng, để tính tiền tiết kiệm/năm | `30` | không |
| `OPT_COMPUTE_COST_PER_HOUR_USD` | Giá tính toán mỗi giờ (USD) | `0.5` | không |
| `OPT_MAX_ATTEMPTS` | Số ứng viên viết lại tối đa | `3` | không |
| `OPT_BENCH_RUNS` | Số lần đo tốc độ (lấy trung vị) | `5` | không |
| `COMPARE_ABS_TOL` | Sai số tuyệt đối khi so kết quả hai query | `1e-6` | không |

## Theo dõi (tùy chọn)

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `LANGCHAIN_TRACING_V2` | Bật LangSmith; tự tắt nếu khóa còn là giá trị mẫu | `false` | không |
| `LANGCHAIN_API_KEY` / `LANGSMITH_API_KEY` | Khóa LangSmith (chấp nhận cả hai tên) | trống | **có** |
| `LANGCHAIN_PROJECT` | Tên dự án LangSmith | `p113-pipeline-agent` | không |
| `AI_LOG_SERVER`, `AI_LOG_API_KEY`, `AI_LOG_DIR` | Ghi log prompt AI của khóa học (xem [CONTRIBUTING.md](../CONTRIBUTING.md)) | — | `AI_LOG_API_KEY` **có** |
