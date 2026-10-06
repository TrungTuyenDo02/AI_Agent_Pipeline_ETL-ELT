# P-113 — Agent viết & tối ưu pipeline ELT/ETL

[![CI](https://github.com/AI20K-Build-Phase-Cohort-4/P-113/actions/workflows/ci.yml/badge.svg)](https://github.com/AI20K-Build-Phase-Cohort-4/P-113/actions/workflows/ci.yml)

> Data engineer mất nhiều giờ viết lặp lại pipeline dbt/Airflow và dò query chậm → agent nhận yêu cầu bằng lời,
> tự sinh model dbt + DAG Airflow, chạy thử trong sandbox DuckDB, đo và tối ưu query, rồi để Engineer duyệt trước khi merge.

**Live URL:** chưa có (giai đoạn C) • **Video demo:** chưa có • **Hướng dẫn chạy chi tiết:** [docs/RUNBOOK.md](docs/RUNBOOK.md)

## Ảnh chụp màn hình

Chụp ở chế độ mô phỏng (`LLM_PROVIDER=mock`), dữ liệu giả lập.

| Cấu trúc dữ liệu (raw → staging → mart, schema, lineage) | Duyệt code (Monaco) + bằng chứng |
|---|---|
| ![Cấu trúc dữ liệu](docs/screenshots/web_catalog.png) | ![Duyệt code](docs/screenshots/web_review.png) |
| **Duyệt kế hoạch J1b** (các bước + vì sao, trước khi sinh code) | **Tối ưu** (trước/sau, đối chiếu từng bộ dữ liệu) |
| ![Duyệt kế hoạch](docs/screenshots/web_plan_review.png) | ![Tối ưu](docs/screenshots/web_optimize.png) |

## Vấn đề

- **Ai gặp:** data engineer (DE) trong đội dữ liệu; người không phải DE nhưng cần pipeline (vận hành, kinh doanh).
- **Đau ở đâu:** mỗi yêu cầu kiểu "gộp đơn hàng 3 nguồn, tính doanh thu ngày" lại phải viết staging, mart, test, DAG
  gần giống nhau; dữ liệu bẩn (trùng đơn, ngày lẫn định dạng, tiền `1.075.000`) dễ làm sai số liệu; query chậm ít ai rảnh tối ưu.
- **Vì sao công cụ hiện có chưa đủ:** trợ lý sinh code thường không chạy thử, không tự kiểm chứng kết quả, và tự báo "xong"
  mà không có bằng chứng — rủi ro cao nếu chạy thẳng trên production.

## Giải pháp

Nguyên tắc **J-E-V**: con người **phán đoán** (J), agent **thực thi** (E), code thuần **kiểm chứng** (V, 0 token).

- **Hỏi trước khi làm:** Planner liệt kê điểm chưa rõ và hỏi dạng trắc nghiệm (J1); còn điểm chưa rõ thì không sinh code.
- **Duyệt kế hoạch trước khi sinh code (J1b):** agent trình bày kế hoạch bằng lời thường, từng bước có giải thích "vì sao"; DE đồng ý hoặc ghi chú để agent lập lại.
- **Sinh pipeline đầy đủ:** model dbt (staging + mart), DAG Airflow, test đối soát do một agent khác viết **không nhìn code**.
- **Kiểm chứng bằng code:** chặn lệnh nguy hiểm và tên bảng/cột bịa (sqlglot), chạy `dbt build` trong sandbox DuckDB
  (không truy cập file ngoài, có timeout), tối đa 3 vòng sửa rồi chuyển con người cứu hộ.
- **Tối ưu có đo đạc:** phát hiện dấu hiệu chậm; thử luật viết lại tất định và sqlglot trước, LLM sau cùng; chỉ áp dụng khi kết quả **giống hệt**
  trên 5 bộ dữ liệu và nhanh hơn ngưỡng; không đáng thì ghi "giữ nguyên" kèm lý do.
- **Duyệt có bằng chứng:** Reviewer xem diff + bảng **"Code đo | LLM nói"**; người tạo yêu cầu không được tự duyệt.

## Người dùng

- **Chính:** DE bận rộn — xem code, diff, số đo.
- **Phụ:** người không phải DE — mô tả nghiệp vụ, xem kế hoạch bằng lời và kết quả mẫu.

## Sơ đồ kiến trúc

![Sơ đồ kiến trúc P-113](docs/adr/architecture.png)

Bản vector: [docs/adr/architecture.svg](docs/adr/architecture.svg) • bản mở trình duyệt: [docs/adr/architecture.html](docs/adr/architecture.html) •
mô tả từng khối + Mermaid: [ARCHITECTURE.md](ARCHITECTURE.md), [docs/architecture_diagram.md](docs/architecture_diagram.md).

| Khối | Loại | Việc |
|---|---|---|
| E1 Planner ⇄ J1 | LLM + người | Lập đặc tả, chọn ELT/ETL (luật cố định), hỏi làm rõ |
| J1b Duyệt kế hoạch | Người | DE đọc kế hoạch có giải thích, đồng ý hoặc yêu cầu sửa (trước khi tốn token sinh code) |
| V0 Soát spec | Code | Chặn nếu còn điểm chưa biết, thiếu trường, mode sai tín hiệu |
| E0 Nhận nguồn → P Soi dữ liệu → E2 Dữ liệu thử | Code | Nạp CSV/JSON/SQLite; hồ sơ cột (đã che PII); bộ small/large/dirty/empty/few/dupkeys/nullmoney |
| E3 Coder → E3b Test-gen | LLM | dbt model + DAG; test đối soát chỉ từ spec + schema |
| V1 An toàn → V2 Sandbox | Code | sqlglot + `dbt build` trên DuckDB; lỗi → sửa (≤3), lỗi lặp → cứu hộ |
| E4 Optimizer ⇄ V3 Đối chiếu | LLM + code | Đề xuất viết lại; đối chiếu hai chiều, đo tốc độ, quyết định applied/skipped |
| Pull Request → J2 Reviewer | Người | Approve / từ chối kèm ghi chú (quay lại Coder) |

## Tech stack

| Lớp | Công nghệ |
|---|---|
| Agent | LangGraph 1.2 (interrupt + checkpointer SQLite), LangChain OpenAI |
| LLM | `mock` (mặc định, không cần khóa); OpenAI theo từng bước (`gpt-5.6-luna` cho planner/codegen/testgen, `gpt-5.6-terra` cho optimizer); dự phòng Google Gemini `gemini-3.1-flash-lite` |
| Sandbox | DuckDB 1.5, dbt-core 1.12 + dbt-duckdb, sqlglot 30 |
| Backend | FastAPI + Uvicorn, SQLite (lần chạy, duyệt, sổ lỗi) |
| Terminal | argparse + rich |
| Frontend | Next.js 16 (App Router) + TypeScript, `@monaco-editor/react` (diff code), sơ đồ dữ liệu SVG tự vẽ |
| DevOps | Docker multi-stage (backend + frontend standalone), docker compose, GitHub Actions (lint → test, frontend → build) |

## Cài đặt và chạy

### Terminal (giai đoạn A — không cần khóa API)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env           # Linux/macOS: cp .env.example .env
python -m src.cli doctor              # kiểm tra môi trường
python scripts/tasks.py demo          # kịch bản mẫu trọn vẹn (máy có make: make demo)
```

Tự chạy từng bước:

```powershell
python -m src.cli seed
python -m src.cli run --request "Gộp dữ liệu đơn hàng 3 nguồn, tính doanh thu ngày" --as engineer --user an
python -m src.cli review latest --as reviewer --user binh
python -m src.cli status
```

### Web trên máy (giai đoạn B)

```powershell
python scripts/tasks.py run           # API ở http://localhost:8000 (make run)
cd frontend; npm ci; cd ..            # một lần
python scripts/tasks.py frontend-dev  # web ở http://localhost:3000 (make frontend-dev)
```

Giao diện thiết kế cho laptop (≥1280px), vẫn dùng được trên màn nhỏ; có giao diện sáng/tối. Các màn hình:

| Màn | Việc DE làm |
|---|---|
| Lần chạy | Tạo yêu cầu bằng lời, xem danh sách lần chạy, lần nào đang chờ mình |
| Tổng quan lần chạy | Trả lời câu hỏi làm rõ (J1), **duyệt kế hoạch có giải thích (J1b)**, cứu hộ, xem tiến trình ✓/✗ từng bước, đặc tả, kết quả mẫu, token/chi phí |
| Duyệt code | Monaco: code dbt/DAG/test (vòng sau: diff với bản đã từ chối), bằng chứng "Code đo \| LLM nói", duyệt/từ chối, tải gói `.zip` |
| Tối ưu | Thời gian trước/sau, đối chiếu kết quả từng bộ dữ liệu, dấu hiệu chậm, diff SQL gốc ↔ bản tối ưu |
| Cấu trúc dữ liệu | Sơ đồ raw → staging → mart, schema từng bảng (kiểu, % rỗng, khóa, trùng khóa), lineage, khóa JOIN |
| Dữ liệu nguồn • Sổ lỗi | 19 bảng raw nhóm theo 8 hệ thống, số dòng, % rỗng, trùng khóa, khóa nối gợi ý kèm % dòng khớp • duyệt bài học cho agent |

### Docker

```powershell
docker compose up --build             # web http://localhost:3000 • API http://localhost:8000/health
$env:LLM_PROVIDER="mock"; docker compose up --build   # ép chế độ mô phỏng dù .env đang chọn openai
```

Dữ liệu của bản Docker nằm trong volume riêng (`backend-data`, `backend-workspaces`), tách với `data/` trên máy;
lần đầu chạy API tự sinh dữ liệu mẫu.

### Kiểm thử

```powershell
python scripts/tasks.py ci            # giống CI: ruff check → ruff format --check → pytest (độ phủ ≥ 60%)
```

## Biến môi trường

Xem giá trị mẫu trong [.env.example](.env.example). Chỉ cần đổi khi muốn dùng LLM thật.

`LLM_PROVIDER`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `MODEL_NAME`, `MODEL_PLANNER`, `MODEL_CODEGEN`, `MODEL_TESTGEN`,
`MODEL_OPTIMIZER`, `LLM_FALLBACK`, `GOOGLE_MODEL_NAME`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `APP_ENV`, `APP_PORT`, `APP_HOST`,
`CORS_ORIGINS`, `LOG_LEVEL`, `STORE_PATH`, `CHECKPOINT_PATH`, `SOURCES_DIR`, `WORKSPACES_DIR`, `SANDBOX_TIMEOUT_SEC`,
`SANDBOX_MEMORY_LIMIT`, `MAX_FIX_ATTEMPTS`, `OPT_MIN_GAIN_PCT`, `OPT_RUNS_PER_MONTH`, `OPT_MAX_ATTEMPTS`,
`MOCK_LARGE_ROWS`, `LANGCHAIN_TRACING_V2` / `LANGSMITH_TRACING`, `LANGCHAIN_API_KEY` / `LANGSMITH_API_KEY`,
`LANGCHAIN_PROJECT`, `AI_LOG_SERVER`, `AI_LOG_API_KEY`, `AI_LOG_DIR`.

## API

Swagger: <http://localhost:8000/docs>. Thao tác làm agent chạy tiếp trả `202` ngay (chạy nền, xếp hàng lần lượt);
web hỏi `GET /runs/{id}` định kỳ để xem tiến trình. Người dùng lấy từ header `X-User` (mặc định `de`); `X-Role` chỉ
dùng khi bật `REQUIRE_SEPARATE_REVIEWER`. Lỗi trả `detail` tiếng Việt, không lộ traceback.

| Method | Path | Mô tả |
|---|---|---|
| GET | `/health` | Trạng thái dịch vụ (`status`, `timestamp`, `version`, `database`, `llm_provider`) |
| GET | `/api/v1/status` | LLM đang dùng, có phải mô phỏng không, chế độ duyệt |
| POST | `/api/v1/runs` | Tạo yêu cầu (`request_text`) → `run_id`, agent chạy nền |
| GET | `/api/v1/runs` • `/runs/{id}` | Danh sách • chi tiết: trạng thái, câu hỏi đang chờ, tiến trình từng bước, đặc tả, bằng chứng, báo cáo tối ưu |
| GET | `/api/v1/runs/{id}/files` | Code + test hiện tại và bản vòng trước (xem diff) |
| GET | `/api/v1/runs/{id}/download` | Gói `.zip` code dbt + test + DAG (không kèm dữ liệu sandbox) để đưa vào repo, mở PR |
| POST | `/api/v1/runs/{id}/answers` | Trả lời câu hỏi làm rõ (J1) |
| POST | `/api/v1/runs/{id}/plan` | Duyệt kế hoạch (J1b): `approve`, hoặc `revise` kèm `note` |
| POST | `/api/v1/runs/{id}/review` | Duyệt / từ chối kèm ghi chú (J2) |
| POST | `/api/v1/runs/{id}/rescue` | Cứu hộ: gợi ý rồi thử lại, hoặc dừng |
| GET | `/api/v1/reviews/queue` | Các lần chạy chờ duyệt |
| GET/POST | `/api/v1/errors` • `/errors/{id}/approve` • `/errors/{id}/discard` | Sổ lỗi |
| GET | `/api/v1/catalog/sources` | Bảng nguồn + schema + gợi ý khóa nối theo tên cột |
| GET | `/api/v1/runs/{id}/catalog` | Cấu trúc một lần chạy: raw → staging → mart, kiểu cột, % rỗng, khóa, lineage, JOIN thật (0 token) |

## Cấu trúc thư mục

```
src/
  cli.py, cli_commands.py, cli_views.py   Giao diện dòng lệnh
  agents/
    graph.py, routing.py, state.py        Graph LangGraph, hàm rẽ nhánh, state (TypedDict)
    runner.py, progress.py                Chạy/tạm dừng/tiếp tục theo run_id, dòng tiến trình
    nodes/                                Mỗi node một file (planner, spec_check, ingest, ... , review)
    tools/                                sql_tools (sqlglot), duckdb_tools, dbt_tools, pii
  api/                                    health, routes, runs
  models/                                 Hợp đồng Pydantic: spec, evidence, schemas
  services/                               llm (+ llm_mock), store, error_memory, seed, doctor, cost, tracing,
                                          company/ (kho raw giả lập P113 Retail), catalog, source_catalog, export, jobs
  prompts/                                Prompt của planner, codegen, testgen, optimizer
pipelines/template/                       Dự án dbt mẫu; workspaces/ sinh lúc chạy (git-ignored)
tests/                                    test_api, test_agents, test_verifiers, test_optimizer, test_services, test_cli
docs/                                     RUNBOOK, adr/ (quyết định + sơ đồ), architecture_diagram.md, guide/
scripts/                                  seed_data.py, tasks.py (thay make trên Windows), hook ghi log AI
```

## Kết quả đánh giá

Chỉ ghi số đã đo thật (2026-10-02, Windows, Python 3.11.9). Tổng hợp tự động: [eval/results/report.md](eval/results/report.md)
(`make eval`). Cột "LLM thật" dùng **openai**: planner/codegen/testgen = `gpt-5.6-luna`, optimizer = `gpt-5.6-terra`.

**Phần kiểm chứng bằng code (không cần LLM, chạy trong CI):**

| Chỉ số | Giá trị | Ghi chú |
|---|---|---|
| Test tự động | 280 passed | `pytest`, độ phủ 90,1% (ngưỡng 60%) |
| Mutation test: bộ kiểm chứng bắt lỗi giả | **11/12 (91,7%)**, 0/1 báo động nhầm | SUM→AVG, bỏ WHERE, bỏ khử trùng, đọc sai ngày/tiền, quên nguồn...; [mutation.md](eval/results/mutation.md) |
| Golden: kết quả đúng (tính tay) khớp SQL chuẩn | 11/11 | [golden_reference.md](eval/results/golden_reference.md) |
| TPC-H sf=0.1: 13 query chậm cố ý | 11/13 áp dụng, nhanh hơn 51%–94,7% | 10/11 nhờ luật tất định (0 token); [tpch_benchmark.md](eval/results/tpch_benchmark.md) |
| ELT-Bench: bộ chấm kiểm bằng model chuẩn | 3/3 khớp | [eltbench_reference.md](eval/results/eltbench_reference.md) |

**Agent chạy bằng LLM thật:**

| Chỉ số | Giá trị | Ghi chú |
|---|---|---|
| Golden 12 ca (trùng đơn, hoàn tiền, ngày lẫn định dạng, nối một-nhiều, PII...) | **12/12 đúng**; 12/12 chọn đúng ELT/ETL; 10/12 không phải sửa vòng nào | ~43 s và ~0,0055 USD mỗi ca; [golden_agent.md](eval/results/golden_agent.md) |
| Hỏi làm rõ khi yêu cầu mơ hồ | Có (2 câu) ở yêu cầu mơ hồ; 0 câu ở 11 yêu cầu đã rõ | ca g10 |
| Kịch bản "gộp 3 nguồn, doanh thu ngày" × 5 lần | 5/5 tới bản duyệt; 4/5 không phải sửa vòng nào | ~19,6 nghìn token, ~0,02 USD/lần (gpt-4o-mini cùng kịch bản: 4/5) |
| ELT-Bench-Verified: agent tự xây 34 bảng (10 pipeline công khai) | **7/34 khớp bảng đúng**; 27/34 đi trọn luồng tới bản duyệt | Bảng còn lại lệch nghĩa so với định nghĩa của benchmark; tổng 0,94 USD; [eltbench_agent.md](eval/results/eltbench_agent.md) |
| Optimizer "tối ưu chỉ khi đáng" | 1 lần nhanh hơn 39,6% nhưng tiết kiệm/năm < chi phí tối ưu → giữ nguyên | đúng luật thiết kế |

## Hạn chế đã biết

- Chưa chạy trên dữ liệu công ty thật; dùng kho raw giả lập của công ty bán lẻ "P113 Retail" (8 hệ thống, 19 bảng, bẩn có chủ đích, seed cố định — [docs/data-catalog.md](docs/data-catalog.md)).
- Kết quả chạy bằng `mock` không phản ánh chất lượng mô hình thật; Planner/Coder mock được viết sẵn cho kịch bản doanh thu ngày.
- Một vai trò DE (tự duyệt) theo quyết định của đội; bật `REQUIRE_SEPARATE_REVIEWER=true` để tách Engineer/Reviewer.
- Bảo mật ở mức tối thiểu: người dùng/vai trò xác định bằng tham số CLI hoặc header `X-User`/`X-Role` (web), chưa có đăng nhập.
- Sandbox chỉ DuckDB local; gợi ý partition/cluster cho kho khác chỉ là gợi ý, không thực thi.
- Chưa có Live URL (giai đoạn C). Web: các lần chạy xếp hàng lần lượt; nhật ký từng bước giữ trong bộ nhớ API (mất khi khởi động lại, kết quả vẫn còn); trình xem code Monaco tải từ CDN jsDelivr nên cần mạng.

## AI usage logging

Mọi prompt được ghi vào `.ai-log/session.jsonl` và tự động gửi lên grading server ở bước pre-push.
Cài hook một lần sau khi clone:

```bash
bash scripts/setup_hooks.sh                                      # Linux / macOS / Git Bash
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1 # Windows PowerShell
```

| Công cụ | Cấu hình | Thời điểm ghi |
|---|---|---|
| Claude Code | `.claude/settings.json` | mỗi prompt (`UserPromptSubmit`) |
| Cursor | `.cursor/hooks.json` | mỗi prompt và khi dừng |
| OpenAI Codex CLI | `.codex/hooks.json` | mỗi prompt và khi dừng |
| Gemini CLI | `.gemini/settings.json` | mỗi lượt agent chạy |
| GitHub Copilot | `.github/hooks/hooks.json` | mỗi prompt và cuối session |
| Antigravity IDE | `.agents/hooks.json` | mỗi prompt, kèm lần quét lại lúc `git push` |

Dùng ChatGPT hay công cụ web khác thì log thủ công:

```bash
bash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "What you asked"
```

Mỗi thành viên tự tạo `AI_LOG_API_KEY` tại [dashboard Phoenix](https://phoenix.note.transformerlabs.ai/api-keys) và điền vào `.env`.

## Thành viên

| Thành viên | Vai trò |
|---|---|
| TrungTuyenDo02 | Toàn bộ hệ thống |

## Deliverables

- [x] Source code (`src/`)
- [x] README.md
- [x] Sơ đồ kiến trúc (`docs/adr/architecture.png`, `docs/architecture_diagram.md`)
- [x] AI logs (hook tự động; LangSmith tùy chọn)
- [ ] Live URL
- [ ] Video demo (`docs/video-demo.md`)
- [ ] Pitch deck (`presentation/`)
- [x] Journal (`JOURNAL.md`)
- [x] Worklog (`WORKLOG.md`)
- [ ] Evaluation evidence (`eval/results/report.md`)

## License

[MIT](LICENSE)
