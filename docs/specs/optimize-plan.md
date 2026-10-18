# Kế hoạch: đo hiệu năng và báo cáo điểm nghẽn (theo `Optimize.md`)

## Đối chiếu với code hiện có

| Mục trong Optimize.md | Đã có | Còn thiếu |
|---|---|---|
| Nguyên tắc: luật → sqlglot → LLM, 6 bộ thử, chạy lại sandbox, `OPT_MIN_GAIN_PCT` | `nodes/optimizer.py`, `compare.py`, `sandbox_run.confirm_optimization` | — |
| Không đưa giá trị thật cho LLM | `schema_for_sql`, `prompt_error` | `explain_outline` gửi cả hằng số trong `Filters/Conditions` vào prompt optimizer |
| 1. Thời gian từng model | `_read_run_results` chỉ lấy `unique_id/status/message` | thời gian compile/execute, rows, materialization, invocation_id, dbt/adapter version; lưu theo lần thử, không ghi đè |
| 2. Bộ eval cố định | TPC-H 13 ca chậm (`eval/benchmarks/tpch/slow`), `ab_optimizer.py`, `benchmark_query` (1 khởi động + 5 lần, trung vị) | độ phân tán/ngưỡng nhiễu; đầu ra `summary.md/cases.csv/details.json`; nhãn "điểm nghẽn đã biết" để chấm |
| 3. Báo cáo điểm nghẽn | `explain_outline` (EXPLAIN ANALYZE JSON), `detect_slow_patterns` (chỉ model đích) | xếp model theo thời gian, top N, phát hiện dạng hiện tượng → bằng chứng → giả thuyết → bước tiếp; tổng model vs thời gian thực |
| 4. Kiểm chứng DAG | `safety.check_dag` (AST: cú pháp, `DAG(...)`, `>>`, bí mật, preflight, lệnh nguy hiểm) | vòng lặp, task mồ côi, lịch/retries/timeout, chặn đích ngoài sandbox; Airflow chưa cài → "chưa kiểm chứng" |
| 4. Ca cố tình sai SQL | `eval/verifier_bench/v3_pairs.yaml`, `eval/mutation` | kiểm lại đủ 3 kiểu (đổi toán tử, bỏ lọc, thêm DISTINCT); thêm ca DAG vòng lặp / sai đích |
| 5. Màn Tối ưu / Reviewer | `OptimizationScreen.tsx`, `ReviewScreen.tsx`, `ReviewDecision` (người duyệt, thời điểm, ghi chú) | bảng thời gian model, điểm nghẽn, nhãn "đã đo/giả thuyết/chưa kiểm chứng/chưa đo", nút duyệt tắt khi kiểm tra bắt buộc không đạt |

## Cách làm (ít code, tái sử dụng)

1. `dbt_tools`: thêm trường tùy chọn vào `DbtNodeResult` (thời gian, rows, materialization); đọc `manifest.json`;
   sao `run_results.json` thành `target/runs/<invocation_id>.json` để không ghi đè. Không chạy thêm dbt.
2. `sandbox_run`: ghi `model_timings` + `wall_ms` vào kết quả V2 (trường tùy chọn).
3. Tool mới `tools/bottleneck.py` (V, 0 token): xếp model, `EXPLAIN ANALYZE` top `PERF_TOP_N`, giới hạn `PERF_ANALYZE_SEC`;
   lỗi → "chưa phân tích được". Hằng số trong plan được che trước khi vào prompt.
4. `safety.check_dag`: thêm kiểm vòng lặp/mồ côi từ chuỗi `>>`, `retries`/`execution_timeout`/`schedule`, đích sandbox.
5. `package`: thêm mục bằng chứng "Kiểm tra bắt buộc" (4 mục) + "Airflow chạy thật: chưa kiểm chứng".
6. eval: script nhỏ dùng lại `tpch/slow` + `benchmark_query`, xuất 3 file, chạy 2 lần so kết luận.
7. Frontend: thêm bảng/nhãn vào 2 màn sẵn có; xử lý thiếu trường (checkpoint cũ) → "chưa đo".

Mỗi bước: test liên quan → `python scripts/tasks.py ci` → commit riêng.

## Trạng thái (2026-10-18)

- Đã làm: bước 1, 3, 4 (backend) theo mục "Cách làm" 1–5. ADR 0017.
- Chưa làm (để đợt sau, theo lựa chọn của chủ dự án): bước 2 (bộ eval cố định, `eval/results/<eval_id>/…`, đo lặp + ngưỡng nhiễu,
  tỷ lệ DAG qua lần đầu) và bước 5 (màn Tối ưu, màn Reviewer). API đã trả `optimization.bottlenecks`, `sandbox.model_timings`,
  và mục "Kiểm tra bắt buộc" trong `evidence.measured` để giao diện dùng.
- Khác đặc tả: `schedule` không bắt buộc (Airflow 2 mặc định hằng ngày), chỉ kiểm giá trị khi có; `retries`/`execution_timeout`
  không bắt buộc. "Khớp manifest.json" ở V1 đối chiếu với file model sẽ vào manifest (manifest chưa có trước khi build).

## Kế hoạch phần còn lại

Đề xuất làm **bước 5 trước rồi bước 2**: bước 5 chỉ cần dữ liệu backend đã có, ít rủi ro, xem được ngay. Bước 2 dài hơn, chạy ngoài
CI (TPC-H cần mạng lần đầu) và có phần tốn tiền nếu dùng LLM thật. Mỗi bước: test → `python scripts/tasks.py ci`
(+ `frontend-check` cho bước 5) → một commit riêng.

### Bước 5 — Hiển thị kết quả (frontend, khoảng 150–200 dòng)

| Việc | File | Loại |
|---|---|---|
| Kiểu mới, mọi trường tùy chọn: `ModelTiming`, `PerfReport`, `Bottleneck`; `Optimization.bottlenecks?`, `Sandbox.model_timings?/wall_ms?` | `frontend/lib/types.ts` | — |
| Bảng thời gian mọi model (model, materialization, compile, execute, số dòng, % tổng) + **hai con số tách biệt** "tổng thời gian các model" / "thời gian thực cả pipeline" | component mới `run/ModelTimings.tsx`, gắn vào `OptimizationScreen.tsx` | V (hiển thị số đo) |
| Thẻ điểm nghẽn có 3 nhãn: **Đã đo** (hiện tượng, bằng chứng) · **Giả thuyết** (giả thuyết, bước tiếp) · **Chưa kiểm chứng** (điều chưa biết); `analyzed=false` → "chưa phân tích được" | `run/Bottlenecks.tsx` | — |
| Màn Tối ưu vẫn hiện khi `decision=skipped`; thiếu số liệu → "chưa đo"; `warehouse_hints` ghi "chưa kiểm chứng, không tính là lợi ích" | `OptimizationScreen.tsx` | — |
| Màn Reviewer: khối "Kiểm tra bắt buộc" (4 mục) + "Bổ sung: chưa kiểm chứng" + quyết định tối ưu, lấy từ `evidence.measured` | `ReviewScreen.tsx` | — |
| Nút **Duyệt** tắt khi kiểm tra bắt buộc không đạt, hiện lý do (giống cách đang chặn khi `drift.recheck.blocked`) | `DecisionForm.tsx` | J (người duyệt) |
| Người duyệt, thời điểm, ghi chú: đã có trong `ReviewDecision`; chỉ cần kiểm màn có hiện chưa, thiếu thì thêm | `ReviewScreen.tsx` | — |
| Dữ liệu demo: thêm 1 ca có bản sửa, 1 ca `skipped`, 1 ca checkpoint cũ (không có trường mới) | `frontend/lib/demo/fixtures.ts` | — |

Kiểm tra: `npm --prefix frontend run lint / format:check / typecheck / check:contrast / lint:text / build`. Đạt khi xem được cả
ca có và không có bản sửa, và ca checkpoint cũ không vỡ giao diện.
Không đụng các file trang đăng nhập đang sửa dở (`login/`, `globals.css`, `loginText.ts`).

### Bước 2 — Bộ eval cố định (khoảng 200–250 dòng Python + 6–8 ca)

1. **Ca thử** `eval/benchmarks/perf/cases/<id>/`: mỗi ca là một dự án dbt nhỏ (2–4 model) + `expected.csv` (đáp án cố định) +
   `case.yaml` (`bottleneck_model`, `bottleneck_operator`, `pattern`). 6–8 ca với điểm nghẽn đã biết: nối theo khoảng, nối nhân
   dòng, DISTINCT thừa, ORDER BY trong truy vấn con, cửa sổ để khử trùng, UNION thay UNION ALL, gom nhóm trước khi lọc,
   cộng thêm 1 ca đối chứng không có điểm nghẽn ("giữ nguyên" là đúng). Dữ liệu sinh tất định bằng `range()` (không cần mạng).
   Dùng lại 13 ca `tpch/slow` (đã có đáp án `tpch:<n>`) cho phần đo tối ưu.
2. **Script** `eval/run_perf.py` (V, 0 token khi mock): với mỗi ca thì chép template → `run_dbt_build` (số đo bước 1) →
   `analyze_bottlenecks` → so `expected.csv` → `optimize_standalone` trên model chậm nhất → đối chiếu bản gốc.
   Không viết lại logic nào, chỉ gọi hàm có sẵn.
3. **Đo công bằng**: 1 lần khởi động + ≥ 5 lần lặp, cố định `SANDBOX_THREADS`, kích thước dữ liệu đủ để trung vị > 50 ms; báo
   trung vị + độ phân tán (MAD hoặc min–max). Ngưỡng nhiễu = độ lệch trung vị giữa 2 lần đo bản gốc; chỉ tính cải thiện khi vượt
   cả ngưỡng nhiễu lẫn `OPT_MIN_GAIN_PCT`.
4. **Chấm riêng từng câu hỏi**: khớp đáp án · bản tối ưu giữ kết quả · đúng model/toán tử trong top N · thời gian trước/sau ·
   token, chi phí LLM · ghi cả bản bị loại và ca giữ nguyên.
5. **Chỉ số DAG** (tỷ lệ qua lần đầu, tỷ lệ qua đủ kiểm tra bắt buộc, số vòng sửa trung bình): đọc từ các lần chạy golden agent
   (`fix_attempts`, `safety` lần đầu). Ở chế độ mock con số luôn là 100%/0 vòng, nên phải ghi rõ "mock". Số thật cần LLM thật.
6. **Đầu ra** `eval/results/<eval_id>/summary.md`, `cases.csv`, `details.json` (`eval_id` = ngày + commit + provider).
7. **Lặp lại**: `--repeat 2` chạy hai lần, báo kết luận đúng/sai có giống nhau không và trung vị có lệch trong ngưỡng nhiễu không.
8. **Test** `tests/test_eval/test_perf_eval.py`: 1 ca tổng hợp nhỏ chạy offline (đánh dấu `slow` vì có dbt thật), kiểm 3 file
   đầu ra, kiểm đúng model nằm trong top N, kiểm `--repeat 2` cho cùng kết luận.
9. Tài liệu: `eval/benchmarks/README.md`, RUNBOOK 4.2, WORKLOG.

### Cần chủ dự án quyết trước khi làm

- **API**: thêm trường `review_gate: {passed, failures}` vào chi tiết lần chạy (chỉ thêm, giống `drift.recheck`) để nút Duyệt
  dùng đúng logic backend, hay để frontend tự suy từ `evidence.measured`? (Khuyên: thêm trường, vì checkpoint cũ không có mục
  bằng chứng mới.)
- **Hợp đồng**: thêm `QueryMetrics.spread_ms` (tùy chọn) để báo độ phân tán?
- **Chi phí**: chỉ số DAG với LLM thật cần chạy golden agent bằng LLM thật. Trước khi chạy sẽ báo số tiền ước tính; nếu không
  thì chỉ báo số mock và ghi rõ.
- **Kích thước TPC-H**: sf 0.1 (khoảng 1 phút) hay sf 1 (sát thực tế hơn, khoảng 300 MB)?

## Trạng thái bước 5 (2026-10-18)

- Đã làm theo quyết định của chủ dự án: `review_gate` ở backend (3 trạng thái, endpoint Duyệt chặn 409), `spread_ms` = IQR,
  tách tổng model / dbt invocation / DAG (DAG "chưa đo"), 3 ca demo trong chế độ khách (`mau-cho-duyet` có bản sửa,
  `mau-giu-nguyen`, `mau-checkpoint-cu`). Không đụng file đăng nhập và README đang sửa dở.
- Tiếp theo: bước 2 (eval) theo mục "Bước 2" ở trên, chạy bằng mock; TPC-H mặc định sf 0.1 (cho phép `--sf 1`, dùng lại file
  `data/tpch_sf<sf>.duckdb` đã tải); tỷ lệ DAG qua lần đầu ở mock ghi "không đánh giá năng lực LLM"; `--repeat 2` lệch kết luận
  → "kết quả chưa ổn định".

## Trạng thái bước 2 (2026-10-18)

- Đã làm: `eval/run_perf.py`, 7 ca `perf/` + 13 ca TPC-H sf 0.1, đầu ra 3 file, `--repeat 2`. Kết quả mock: đúng 20/20, điểm
  nghẽn 6/6, tối ưu áp dụng 15 (giữ kết quả 15/15); kết luận hai lượt giống nhau nhưng thời gian lệch quá ngưỡng nhiễu ở 6 ca →
  "kết quả chưa ổn định" (máy đo là laptop).
- Còn mở (chờ chủ dự án quyết):
  - Chạy thật bằng LLM: cần báo riêng số ca, model, chi phí ước tính.
  - Ổn định thời gian: đo trên máy yên tĩnh hoặc tăng `OPT_BENCH_RUNS`. Không nới ngưỡng.
  - Optimizer bỏ sót nối theo khoảng và nối nhân dòng ở bước dò dấu hiệu tĩnh. Có thể cho optimizer dùng báo cáo điểm nghẽn
    làm tín hiệu (việc riêng).
  - README "Hạn chế đã biết" chưa cập nhật vì README đang có thay đổi chưa commit của chủ dự án.
