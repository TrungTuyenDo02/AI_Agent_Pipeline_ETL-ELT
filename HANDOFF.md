# HANDOFF — Đợt B tạm dừng/tiếp tục trên cloud, đã xử lý review vòng 2 (2026-10-18)

## Việc vừa làm

- Nhánh: `wip/cloud-pause-resume-2026-10-18` (tách từ `feat/guest-mode` tại `aa6822f`). Commit snapshot `9fe2193` + `16fd218`
  (hoàn thiện Đợt B) + commit sửa review vòng 2. Chưa merge, chưa mở PR.
- Đợt A (giao diện) giữ nguyên, không sửa. `frontend-check` chạy lại trên cloud: xem mục kết quả.
- Đợt B: logic có sẵn trong snapshot giữ nguyên trừ 2 sửa nhỏ ở `src/services/store.py` (bên dưới). Phần lớn công việc là tái hiện,
  kiểm chứng và bổ sung test. ADR [0016](docs/adr/0016-tam-dung-tiep-tuc-lan-chay.md) đã viết; API.md, RUNBOOK, README, WORKLOG
  đã cập nhật.

## Hai test lỗi trong log cũ — nguyên nhân

- `test_pause_while_node_runs_finishes_node_then_stops_before_next`: **test sai giả định**. Graph là `planner → spec_check (V0) →
  clarify (J1)` (`routing.after_planner`). Node kế tiếp sau planner đúng là `spec_check`. Đã sửa kỳ vọng và siết thêm: `spec_check`
  và `clarify` chưa chạy, checkpoint có `spec` nhưng chưa có `spec_errors`.
- `test_resume_refused_when_budget_or_limits_hit`: **test sai giả định**. LLM mock trả 0 token (`llm_mock._usage`), nên đã dùng
  0 < 1 và 202 là đúng. Đã giả lập 500 token/lượt như `test_token_budget_stops_run_with_clear_message`, trần 400, giữ kỳ vọng 409
  `RUN_TOKEN_BUDGET`.

## Sửa implementation

- `Store.request_pause` lỗi **trên PostgreSQL** (`AmbiguousParameter`: cùng tham số `:id` vừa là cột VARCHAR khi INSERT vừa là text
  khi so sánh). SQLite không bắt được. Tách thành `:new_id`. Phát hiện bằng PostgreSQL 16 tạm trong container.
- `fail_interrupted_runs`: lần chạy đang chờ tạm dừng thành `paused` thì xóa `summary.error` cũ (ví dụ lượt trước lỗi rồi chạy lại),
  chỉ giữ `notice`.

## Test thêm (tests/test_api/test_pause_api.py, 17 test)

- Trần USD của lần chạy và ngân sách hệ thống hôm nay (409, vẫn `paused`, dưới trần thì chạy tiếp được).
- Chưa đăng nhập 401, thiếu `X-Requested-With` 403, bị chặn thì không ghi `run.resume`.
- Đang chạy: `resume`/`retry` → 409, không chạy trùng.
- Khởi động lại khi node đang chạy và có yêu cầu tạm dừng: thành `paused`, tiếp tục chỉ làm lại planner, không chạy lại G0/G1.
- Test restart cũ đếm `fail_interrupted_runs() == 0` trên store dùng chung cả phiên, nên lỗi khi chạy cả bộ. Đã đổi sang kiểm đúng
  lần chạy của test (trạng thái, tóm tắt không đổi, không có lỗi).

## Vòng review 2 (sau commit `16fd218`): hai lỗi thật, đã sửa

Viết test tái hiện trước, cả 3 test lỗi trên code cũ: `KeyError: 'patch_of'` (2 test) và `[202, 202]` thay vì `[202, 429]`.

1. **Run vá tạm dừng khi còn xếp hàng mất đầu vào bản vá.** Runner kiểm cờ tạm dừng trước khi graph nhận đầu vào, nên checkpoint
   rỗng; `continue_run` dựng lại đầu vào từ bản ghi và đi `input_gate` → Planner thay vì `patch_start`. Sửa: `runner.prepare_patch`
   ghi đầu vào bản vá vào checkpoint ngay trong `POST /runs/{id}/patch`, trước khi xếp hàng (chỉ bước nhận đầu vào + định tuyến START,
   0 token, dừng trước `patch_start`). `run_patch` bỏ qua nếu đã ghi. Không ghi được → run vá `failed`, API 500.
   Test: `tests/test_schema_drift.py::test_patch_run_paused_in_queue_keeps_patch_input[resume|restart-then-resume]`: đầu vào có
   trong checkpoint khi còn xếp hàng; tạm dừng; (khởi động lại); tiếp tục → `waiting_review` qua `patch_start`, không G0/G1/Planner/
   J1/J1b, Planner 0 lượt gọi, 0 token, bảng đích giống run gốc.
2. **Hai run khác nhau cùng tiếp tục vượt `max_active_runs_per_user`.** `check_limits` và `submit` tách rời. Sửa:
   `JobQueue.submit(..., limits=True)` kiểm giới hạn trong cùng khóa với nhận vào hàng, sau `guard`; API `resume` bắt
   `JobLimitError` → 429. Bị từ chối thì chưa đổi gì nên vẫn `paused`, không ghi `run.resume`. Trong khóa chỉ đọc DB, không gọi lại
   hàng đợi (khóa không tái nhập) nên không kẹt. Test: `test_concurrent_resume_of_two_runs_respects_active_limit` dùng
   `threading.Barrier(2, timeout=1)` để ép hai yêu cầu cùng tới bước kiểm; sau bản sửa bên thứ hai bị khóa giữ lại, bên thứ nhất chờ
   hết hạn rồi đi tiếp (kiểm luôn việc không kẹt).

## Kết quả kiểm chứng (phiên cloud)

- `python -m pytest tests/test_api/test_pause_api.py`: 17 passed ở vòng 1 (chạy lặp 5 lần đều đạt); 18 sau vòng 2.
- PostgreSQL 16 tạm (`p113_test`, `STATE_BACKEND=postgres`, `RUN_WORKERS=1`): pause + auth/migration + retry + runs API 63 passed.
  Migration lên `0010_run_controls`, GRANT cho `p113_app` đúng; vòng downgrade/upgrade qua `test_migrations_run_from_scratch...`.
  Với `RUN_WORKERS` mặc định (nhiều luồng), `test_pause_while_queued_never_starts` không áp dụng vì lần chạy thứ hai không xếp hàng.
- Headless Chromium (backend mock + `next start`): nút chỉ hiện cho Engineer tạo yêu cầu; Engineer khác, Reviewer, chưa đăng nhập,
  khách đều không thấy; sáng/tối × 1366/390 px không tràn ngang, 0 lỗi trang. Bấm **Tiếp tục** → `waiting_clarification`.
  Uvicorn khởi động lại thật đã chuyển lần chạy "đang chờ tạm dừng" thành "đã tạm dừng" kèm lời nhắc.
- Vòng 1, `python scripts/tasks.py ci` và `frontend-check`: `ci` exit 0: ruff check/format đạt; pytest **1211 passed, 31 skipped,
  2 xfailed**, độ phủ **92,01%** (8 phút 18 giây). 31 skipped có sẵn từ trước: 20 `test_connectors` (cần `RUN_PG_TESTS=1`),
  5 `test_state_postgres` (cần `TEST_DATABASE_URL` PostgreSQL), 6 `test_prompts/test_budget` (không tải được bộ mã tiktoken trong container). `frontend-check` exit 0: lint,
  format:check, typecheck, check:contrast, build đều đạt.

- Vòng review 2: `ci` và `frontend-check` cuối: `ci` exit 0: ruff check/format đạt; pytest **1214 passed, 31 skipped, 2 xfailed**,
  độ phủ **91,99%** (8 phút 51 giây; cùng 31 skip có sẵn như vòng 1). `frontend-check` exit 0: lint, format:check, typecheck,
  check:contrast, build đều đạt. Lần chạy này diễn ra trước khi điền số liệu vào HANDOFF/README/WORKLOG; sau đó chỉ sửa tài liệu,
  đã chạy lại `check_worklog`.
- PostgreSQL 16 tạm (`STATE_BACKEND=postgres`, `RUN_WORKERS=1`), vòng 2: `test_pause_api.py` + 2 test run vá mới + test run vá cũ:
  21 passed.

## Chưa kiểm chứng

- PostgreSQL thật (Neon) và nhiều luồng thật sự song song trên PostgreSQL; Docker.
- Kill tiến trình thật giữa một lời gọi LLM/dbt (đã mô phỏng bằng checkpoint dừng trước planner + `fail_interrupted_runs`).
- LLM thật: không gọi trong phiên này.

## Cần chủ dự án review

- Hợp đồng: `RunStatus.PAUSED`, `RunRecord.pause_requested=False`, 2 endpoint mới, `Accepted.status` thêm `pausing`/`paused`
  (chi tiết ADR 0016 mục "Hợp đồng"). Tương thích: trường mới có mặc định; checkpoint cũ không đổi khuôn; test API cũ đều đạt.
- Hành vi mới: mọi hành động đưa lần chạy đang bận vào hàng lần nữa nay trả 409 (trước 202 rồi bị bỏ trong luồng nền).
- Còn lại ngoài phạm vi: tạo yêu cầu, trả lời J1/J2, chạy lại và tạo run vá vẫn kiểm hạn mức ngoài khóa như trước ADR 0016;
  hai yêu cầu đồng thời của cùng người vẫn có thể cùng lọt. Chưa sửa vì không thuộc tạm dừng/tiếp tục.
- Run vá tạm dừng khi xếp hàng bằng code trước `16fd218`+bản sửa này không có checkpoint đầu vào, không khôi phục được (chỉ có ở
  máy thử WIP).

## Việc tiếp theo

1. Review diff, quyết định hợp đồng; mở PR khi đồng ý.
2. Backlog: receipt từng run và phân giải `source_id` khi trùng tên bảng.

## Baseline trước đợt giao diện/pause-resume

## Đã xong
- Extract: lọc file/bảng SQLite theo allowed_tables trước đọc dữ liệu; cache phân biệt phạm vi quyền.
- Dataset eval/datasets/extract_v1 có nguồn/oracle đóng băng riêng, 21 ca, receipt source_id/file/hash/schema/digest.
- eval-extract chạy độc lập; run_eval tích hợp điểm Extract và truyền lỗi tiến trình con.
- Sửa `.claude/rules/api.md`: cookie phiên, vai trò từ backend, CSRF; cập nhật đường dẫn test.
- So bảng vá theo tên/thứ tự/kiểu cột và số lần xuất hiện từng dòng; hỗ trợ dữ liệu lồng nhau và NaN.
- Giữ các trường regression cũ; thêm schema_same và ghi rõ đổi cấu trúc trên bằng chứng/tiến trình.
- Bỏ khối lặp trong frontend/CLAUDE.md cục bộ; CLAUDE.md tiếp tục bị Git bỏ qua theo ý người dùng.
- README, report, RUNBOOK, WORKLOG đã đồng bộ với bản sửa và kết quả CI.

## Trạng thái kiểm chứng lịch sử (không phải snapshot WIP hiện tại)
- `python scripts/tasks.py ci`: 1149 passed, 20 skipped, 2 xfailed, độ phủ 91.85%; không có failure.
- Frontend: lint, format:check, typecheck, check:contrast, build đều qua.
- Docker chưa kiểm tra vì máy không có lệnh docker.

## Backlog ở bàn giao trước (đã được ưu tiên lại ở trên)
1. Tiếp theo: receipt cho từng run và phân giải source_id khi trùng tên bảng; eval hiện chọn nguồn tường minh.
2. Bàn giao trước còn yêu cầu xem diff và commit. Phiên hiện tại đóng gói thành snapshot WIP theo yêu cầu người dùng.
3. Có thể kiểm tra Docker bằng CI GitHub sau khi push.

## Quyết định cần nhớ
- Giữ nguyên tên node và hợp đồng Pydantic; checkpoint cũ chưa có schema_same vẫn đọc được.
- Chỉ số pytest được cập nhật từ CI; chưa chạy lại phép đo LLM thật hoặc golden/mutation trong phiên này.

- Extract eval 21/21 (tổng hợp, không mạng/LLM); chưa chấm PostgreSQL thật, native phức tạp/múi giờ hay CDC.
