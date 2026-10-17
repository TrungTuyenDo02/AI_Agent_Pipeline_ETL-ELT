# Bàn giao P-113 cho Claude Code Cloud

Ngày: 2026-10-18 (giờ Việt Nam). Nhánh: `wip/cloud-pause-resume-2026-10-18`.
Điểm gốc trước snapshot: `aa6822f` trên `feat/guest-mode`.

## Phạm vi

Hoàn thiện Đợt B: tạm dừng/tiếp tục lần chạy, bảo toàn Đợt A và chức năng đang có. Đọc [HANDOFF](../HANDOFF.md) để biết phần đã viết và kết quả test còn lỗi. Các thay đổi sẵn có trong README, báo cáo và giao diện được giữ lại trong snapshot; không tự hoàn tác vì không thuộc phần mình viết.

`CLAUDE.md` ở root và các thư mục con bị Git bỏ qua theo lựa chọn của chủ dự án. Tài liệu này mang các quy tắc cần thiết lên cloud; không cần force-add các file đó, tài khoản hay cấu hình cá nhân.

## Bản đồ file cần bắt đầu

- Backend: `src/agents/runner.py`, `src/services/jobs.py`, `src/services/store.py`, `src/api/runs.py`, `src/main.py`, `src/agents/stages.py`, `src/cli_views.py`.
- Hợp đồng đang sửa dở: `src/models/schemas.py`.
- Migration: `migrations/versions/0010_run_controls.py`.
- Test tái hiện: `tests/test_api/test_pause_api.py`; fixture trong `tests/conftest.py`; kiểm thử liên quan ở `tests/test_agents/`, `tests/test_api/`, `tests/test_services/`.
- Frontend: `frontend/components/run/PauseControl.tsx`, `RunHeader.tsx`, `frontend/lib/types.ts`, `format.ts`, `runFilters.ts`, `runLog.ts`, `frontend/components/StatusPill.tsx`.
- Graph: `src/agents/graph.py`, `routing.py`, `state.py`. Tìm đúng hàm và đọc đoạn liên quan; không đọc cả repo.
- Quy tắc API/SQL còn được Git lưu trong `.claude/rules/api.md` và `.claude/rules/sql-safety.md`.

## Hành vi cần kiểm chứng

1. Tạm dừng lúc một node đang chạy: để node hoàn tất, lưu checkpoint rồi dừng trước node kế tiếp; không ngắt giữa một lời gọi LLM/dbt. UI giải thích bước hiện tại vẫn có thể phát sinh chi phí AI.
2. Tạm dừng khi xếp hàng: không chạy planner/LLM trước khi tiếp tục.
3. Resume từ checkpoint: không chạy lại node đã xong hoặc tính phí lại phần đó; vẫn đi qua đúng các bước chờ người hiện có.
4. Bấm lặp/đồng thời: không tạo hai job chạy cùng run, không kẹt khóa hoặc cờ pause.
5. Chỉ Engineer tạo run được pause/resume. Reviewer, Admin, Engineer khác và khách không có thêm quyền. Backend kiểm quyền độc lập với UI; giữ CSRF.
6. Restart khi đã paused hoặc đang chờ pause phải xử lý checkpoint/trạng thái nhất quán; không tự làm lại phần đã xong.
7. Run tự tới bước chờ người, hoàn thành hoặc lỗi trong lúc có cờ pause phải giữ đúng trạng thái; lỗi còn dùng được retry như cũ.
8. Resume kiểm hạn mức hoạt động, token và ngân sách thực tế; từ chối không được làm mất trạng thái paused. Có audit `run.pause`, `run.paused`, `run.resume` theo hành vi triển khai.

Log cũ có 10 passed/2 failed; đây là mục tiêu để tái hiện, không phải giấy bảo đảm các hành vi còn lại đã đúng. Test restart hiện có cần được xem xét đủ mạnh hay chưa. Không sửa kỳ vọng chỉ để test xanh.

## Môi trường cloud

Dùng Python 3.11 và Node 22 như CI. Không chuyển `.env`, `.env.render`, dữ liệu tài khoản, DB local hoặc API key từ máy người dùng. Cloud dùng dữ liệu giả, SQLite tạm và mock; không cần Neon hay khóa LLM thật.

Nếu chưa có virtualenv/dependencies, chạy từ root trên Linux cloud:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm --prefix frontend ci
export APP_ENV=test
export LLM_PROVIDER=mock
export LLM_FALLBACK=none
export LANGCHAIN_TRACING_V2=false
export LANGSMITH_TRACING=false
export DBT_SEND_ANONYMOUS_USAGE_STATS=false
```

Nếu `python3.11` chưa có, chọn/cài đúng phiên bản trong môi trường cloud; không tự sửa requirements để vượt lỗi cài đặt. Chỉ cài từ các file phụ thuộc hiện có. Không in biến môi trường hoặc thông tin xác thực của nền tảng cloud. Không đặt lại khóa môi trường nền tảng mà Claude Code dùng để hoạt động.

`tests/conftest.py` tự tạo secret ngẫu nhiên, tài khoản và SQLite tạm, cô lập store/checkpoint/nguồn/workspace và ép mock. Để `TEST_DATABASE_URL` không được cấu hình và không đặt `RUN_PG_TESTS=1`; không mang kết nối dev/prod vào môi trường này. Không cần chạy `alembic upgrade head` trên DB bên ngoài để chạy pytest. Khi thử migration PostgreSQL, chỉ dùng DB kiểm thử riêng nếu đã có cấu hình được phép; thiếu thì ghi rõ chưa kiểm chứng.

Chạy test hẹp trước (tắt coverage chỉ cho lượt chẩn đoán này), sau đó kiểm tra đầy đủ:

```bash
python -m pytest tests/test_api/test_pause_api.py -q --no-cov -o addopts=''
python scripts/tasks.py ci
python scripts/tasks.py frontend-check
```

Lệnh CI cuối vẫn phải giữ coverage tối thiểu 60% theo cấu hình repo. Khi lệnh lỗi, xử lý rồi chạy lại phần liên quan trước khi chạy kiểm tra cuối; không báo xong ở kết quả giữa chừng hoặc dựa vào exit code của `tail`. Nếu hết thời gian, ghi tiến độ thực tế và test chưa chạy hết.

## Quy tắc dự án mang từ hướng dẫn cục bộ

- Mục tiêu đầu tiên: pipeline đúng kết quả; sau đó mới tới chi phí và tốc độ. Người phán đoán (J), agent thực thi (E), code thuần kiểm chứng (V). V không gọi LLM.
- Tính năng mới và bản sửa phải chạy với `LLM_PROVIDER=mock`. Mọi lời gọi LLM của ứng dụng đi qua `src/services/llm.py`; prompt nằm trong `src/prompts/`.
- Testgen chỉ nhận spec/schema, không nhận code của Coder. Giữ độc lập kiểm chứng.
- Không chạy pipeline sinh ra trên production; sandbox là DuckDB local. Không thêm đường ghi vào kho thật. Kết nối nguồn chỉ đọc.
- Ngữ cảnh gửi LLM qua `build_llm_context(...)` theo mức quyền; lỗi qua `scrub_error()`. Không đưa dữ liệu thật chưa che, mật khẩu, API key hay chuỗi kết nối vào prompt/log/state/checkpoint/tracing.
- Không đọc, sửa hoặc commit `.env` và các cấu hình chứa bí mật. Không dùng `out/accounts.csv`; tạo tài khoản giả bằng fixture.
- Không sửa hooks ghi log AI trong `.claude/settings.json`, `scripts/*hook*` hoặc `.ai-log/`.
- Không đổi tên node graph, không mở rộng thêm hợp đồng `src/models/` ngoài phần pause/resume đang được bàn giao. `PAUSED` và `pause_requested=False` là thay đổi WIP có sẵn, chưa phải xác nhận duyệt thiết kế. Kiểm tra tương thích checkpoint/API cũ và ghi rõ kết quả cho người dùng review.
- Không thêm MCP, thư viện lớn hoặc đổi model. Model ứng dụng lấy từ `config/models.yaml` và cấu hình hiện có; không hardcode model/khóa.
- Giữ giới hạn vòng sửa và cơ chế cứu hộ. SQL phải qua sqlglot; giữ hàng rào tên bảng/cột và lệnh nguy hiểm.
- Optimizer chỉ áp dụng khi đối soát đúng trên 6 bộ small/dirty/empty/few/dupkeys/nullmoney, đối soát lại sandbox và đạt ngưỡng tăng tốc; lỗi hoặc lệch thì giữ/khôi phục bản gốc.
- Không xóa hàng loạt, không xóa/skip test hay giảm ngưỡng để qua CI. Không sửa file sinh ra trong `pipelines/workspaces/`.
- Không tự đọc `.ai-log/`, `.kilo/`, `.agents/`, `.codex/`, `.cursor/`, `.gemini/`, `presentation/`, `eval/results/` hoặc JOURNAL. Chỉ mở WORKLOG để cập nhật việc của phiên; không quét lịch sử ngoài phạm vi.
- Giao diện, thông báo lỗi và báo cáo bằng tiếng Việt. Tên biến/hàm/file bằng tiếng Anh.
- API lấy người dùng/vai trò từ cookie phiên qua dependency backend; không tin header vai trò do client tự gửi. Thao tác ghi cần `X-Requested-With`; job chạy nền trả 202, lỗi có `detail` tiếng Việt, không lộ traceback. Endpoint mới phải có test và tài liệu API.
- Frontend không gọi LLM hoặc giữ API key; gọi backend `/api/v1/...`. Kiểm tra sáng/tối, laptop và điện thoại. Giữ Monaco/SVG hiện có; không thêm thư viện UI lớn.
- Next.js phiên bản 16.3.8: đọc hướng dẫn phiên bản liên quan trong `frontend/node_modules/next/dist/docs/` trước khi sửa code dùng API Next. Đây là ngoại lệ có phạm vi; không quét toàn bộ node_modules hay `.next/`.
- Không gọi LLM thật, chạy benchmark tốn tiền, deploy, tự merge hoặc sửa production trong phiên này. Mâu thuẫn đặc tả/code ảnh hưởng quyết định sản phẩm thì ghi rõ và hỏi; không tự thay mục tiêu.

## Hoàn tất phiên cloud

- Sửa nguyên nhân hai test lỗi và bổ sung kiểm thử cần thiết cho lỗi thực tế; ghi riêng phần chưa kiểm chứng như PostgreSQL thật hoặc restart tiến trình nếu chưa thử.
- Viết ADR 0016 và đồng bộ WORKLOG, README, RUNBOOK, API.md cùng HANDOFF; không cập nhật số đo dựa trên suy đoán.
- Chuẩn bị commit/diff review trên nhánh làm việc của cloud, không merge vào main hoặc đẩy sang remote `cohort`.
- Sau Đợt B mới quay lại backlog receipt mỗi run/source_id khi trùng tên bảng.
