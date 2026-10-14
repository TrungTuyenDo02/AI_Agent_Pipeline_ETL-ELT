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
| `LLM_FALLBACK` | `google` = model chính gọi lỗi hoặc đang ngắt mạch thì chuyển Gemini; `none` = tắt (vẫn có ngắt mạch, báo lỗi ngay) | `google` | không |
| `BREAKER_MIN_CALLS` • `BREAKER_FAILURE_RATE` • `BREAKER_RESET_SEC` • `BREAKER_PROBES` | Circuit breaker mỗi cặp nhà cung cấp × model: đủ ≥ 4 lượt trong 10 lượt gần nhất và ≥ 50% lỗi thì ngắt 60 giây, rồi cho 1 lượt thăm dò; thành công thì đóng lại | `4` • `0.5` • `60` • `1` | không |
| `STATE_BACKEND` • `RUN_WORKERS` | `sqlite` (mặc định) hoặc `postgres` (Neon) cho lần chạy, sổ lỗi, bộ nhớ agent, checkpoint; số lần chạy cùng lúc (chỉ có tác dụng với postgres) | `sqlite` • `2` | không |
| `LLM_TEMPERATURE` | Chỉ Codegen dùng, tối đa 0,2; bước khác luôn 0 (Opus 5.5 không nhận temperature) | `0` | không |
| `LLM_MAX_TOKENS` | Trần token đầu ra chung (mỗi bước có trần riêng nhỏ hơn) | `16000` | không |
| `LLM_STRUCTURED_OUTPUT` | Gửi JSON Schema strict; `false` = quay về `json_object` | `true` | không |

Mục `input_gate` trong `models.yaml` là model của **tầng 2 cửa kiểm tra đầu vào** (thay cho biến `MODEL_GATE` mà CLAUDE.md bản 2 nêu: dự án cấm tên model ở biến môi trường): model rẻ nhất đang dùng, khác nhà cung cấp với Planner, trần đầu ra 200 token.

**Tên model** không đặt bằng biến môi trường: chỉ khai báo trong [config/models.yaml](../config/models.yaml) (mỗi bước một dòng `provider` + `name`, Anthropic thêm `effort`; mục `fallback` là model Gemini). Hiện tại: Planner/Codegen/Testgen = `gpt-5.6-luna`, Optimizer = `claude-haiku-5-5` (không đặt effort), dự phòng = `gemini-3.1-flash-lite`. Các biến cũ `MODEL_NAME`, `MODEL_<BƯỚC>`, `GOOGLE_MODEL_NAME` không còn tác dụng.

## Cửa kiểm tra đầu vào và trần chi phí

Luật cố định (mẫu tấn công prompt, động từ nghiệp vụ, bảng đồng nghĩa, từ viết tắt kỹ thuật) nằm ở [config/input_gate.yaml](../config/input_gate.yaml): sửa file là đủ, không cần sửa code.

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `INPUT_MIN_CHARS` • `INPUT_MAX_CHARS` | Yêu cầu ngắn hơn / dài hơn bị chặn ở tầng 0 | `10` • `2000` | không |
| `INPUT_GATE_CACHE_SIZE` | Số kết quả kiểm tra nhớ cho câu giống hệt (chuẩn hóa rồi băm); `0` tắt | `512` | không |
| `MAX_CLARIFY_ROUNDS` | Tối đa số vòng hỏi làm rõ mỗi lần chạy; quá số vòng thì dừng, chuyển cho kỹ sư dữ liệu | `2` | không |
| `RUN_TOKEN_BUDGET` | Trần token (vào + ra) mỗi lần chạy, cộng dồn cả các lượt chạy tiếp; vượt thì dừng và báo rõ; `0` không chặn | `200000` | không |
| `USER_DAILY_RUN_LIMIT` | Số lần chạy tối đa mỗi người mỗi ngày (giờ VN); lần bị chặn ở cửa kiểm tra không tính; `0` không chặn | `30` | không |

## Sổ nguồn, mức truy cập của LLM, bí mật nguồn

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `LLM_ACCESS_DEFAULT` | Mức dữ liệu AI được xem cho nguồn **đăng ký mới**: `schema_only` (chỉ cấu trúc), `profile` (thống kê + dạng giá trị, không dòng thật), `masked_sample` (vài dòng đã che). Nguồn `high` ép về `schema_only`, `medium` tối đa `profile`. Đặt `schema_only` để quay về quyết định ban đầu "chỉ cho xem schema" | `profile` | không |
| `LLM_SAMPLE_MAX_ROWS` | Trần số dòng đã che ở mức `masked_sample` | `5` | không |
| `REQUIRE_SEPARATE_REVIEWER` | `true`: người tạo yêu cầu không tự duyệt được ([ADR 0006](adr/0006-tach-nguoi-tao-va-nguoi-duyet.md)); `false` khi chạy demo cá nhân | `true` | không |
| `P113_SECRET_<TÊN IN HOA>` | Giá trị thật của bí mật có tên tham chiếu `<tên>` ở sổ nguồn (chuỗi kết nối, đường dẫn thư mục dữ liệu). Chỉ lớp kết nối đọc; lọc khỏi môi trường của dbt, không vào prompt/log/state | trống | **có** |
| `CONNECTOR_TIMEOUT_SEC` | Thời hạn kết nối và mỗi truy vấn của bộ nạp nguồn (PostgreSQL: `statement_timeout`) | `15` | không |
| `SANDBOX_LOAD_MAX_ROWS` | Số dòng tối đa mỗi bảng nạp vào sandbox; bảng lớn hơn chỉ nạp một tập con có hạt giống cố định (cùng giới hạn → cùng tập con) | `100000` | không |
| `SANDBOX_HASH_SENSITIVE` | Băm cột nhạy cảm (tên gợi ý thông tin cá nhân hoặc admin đánh dấu) khi nạp sandbox: `auto` chỉ nguồn độ nhạy cảm `high`, `always` mọi nguồn, `never` không băm. Băm SHA-256 có muối, nhất quán giữa các bảng nên JOIN còn đúng | `auto` | không |
| `SANDBOX_HASH_SALT` | Muối băm cột nhạy cảm; đặt giá trị bí mật khi triển khai (trống: muối mặc định, chỉ đủ cho demo) | trống | **có** |
| `SECRETS_DIR` | Thư mục chứa bí mật dạng file (mỗi file một tên tham chiếu, kiểu Docker/Kubernetes secrets), thay cho biến môi trường | trống | không |

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

## Giám sát thay đổi cấu trúc nguồn

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `DRIFT_CHECK_TOKEN` | Khóa nội bộ cho `POST /api/v1/sources/check-drift` (header `X-Drift-Token`); trống = kiểm tra định kỳ tắt | trống | **có** |
| `DRIFT_GATE_ENABLED` | Bật cửa G1: so cấu trúc nguồn với bản chuẩn trước Planner, thay đổi `breaking` chặn run | `true` | không |
| `DRIFT_NULL_PCT_DELTA` | % rỗng của cột tăng hơn chừng này điểm phần trăm → cảnh báo | `20` | không |
| `DRIFT_ROWCOUNT_RATIO` | Số dòng lệch hơn chừng này lần (tăng hoặc giảm) → cảnh báo | `3` | không |
| `CAST_FAIL_THRESHOLD` | Tỷ lệ dòng không ép được kiểu tối đa trong pipeline sinh ra; vượt thì test dbt fail | `0.01` | không |

Bảng kiểu "mở rộng an toàn", ngưỡng tên cột giống nhau (nghi đổi tên), ngưỡng dạng giá trị mới và độ lệch khoảng giá trị nằm ở `config/drift_rules.yaml`.

## Theo dõi (tùy chọn)

| Biến | Ý nghĩa | Mặc định | Bí mật |
|---|---|---|---|
| `LANGCHAIN_TRACING_V2` | Bật LangSmith; tự tắt nếu khóa còn là giá trị mẫu | `false` | không |
| `LANGCHAIN_API_KEY` / `LANGSMITH_API_KEY` | Khóa LangSmith (chấp nhận cả hai tên) | trống | **có** |
| `LANGCHAIN_PROJECT` | Tên dự án LangSmith | `p113-pipeline-agent` | không |
| `AI_LOG_SERVER`, `AI_LOG_API_KEY`, `AI_LOG_DIR` | Ghi log prompt AI của khóa học (xem [CONTRIBUTING.md](../CONTRIBUTING.md)) | — | `AI_LOG_API_KEY` **có** |
