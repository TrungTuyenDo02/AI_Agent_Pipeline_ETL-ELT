# ADR 0017 — Đo thời gian từng model và báo cáo điểm nghẽn bằng code (V, 0 token)

- Ngày: 2026-10-18 • Trạng thái: đã chấp nhận (chủ dự án đồng ý thêm trường tùy chọn vào hợp đồng)

## Quyết định

- Số đo lấy từ artifact của lần `dbt build` đã chạy trong V2 (`run_results.json` + `manifest.json`), không chạy thêm dbt.
  Mỗi lần build được lưu riêng ở `target/runs/<invocation_id>.json` (kèm SQL đã biên dịch) để lệnh sau không ghi đè.
- Báo cáo điểm nghẽn tính ở `package` (một lần, trên pipeline cuối): xếp model theo `execute_ms`, `EXPLAIN ANALYZE` tối đa
  `PERF_TOP_N` model trong `PERF_ANALYZE_SEC` giây. Mỗi phát hiện gồm hiện tượng, bằng chứng (đã đo), giả thuyết và bước kiểm tra tiếp
  (chưa kiểm chứng). Giả thuyết không vào `evidence.measured`. Lỗi → "chưa phân tích được", không làm hỏng lần chạy.
- Báo hai con số tách biệt: tổng thời gian các model và thời gian thực của cả lệnh dbt.
- Kế hoạch thực thi đưa cho LLM (`explain_outline`) đã che hằng số; báo cáo điểm nghẽn chỉ chứa tên toán tử, thời gian, số dòng.
- 4 kiểm tra bắt buộc (model chạy, DAG, dbt tests, kết quả khớp kỳ vọng) tính ở `src/agents/review_gate.py`, 3 trạng thái
  `passed`/`failed`/`unverified`; thiếu bằng chứng (checkpoint cũ) = `unverified`, không tính là đạt. Cổng chặn duyệt ở
  `runner.check_review` (API 409, CLI) và trả trong `GET /runs/{id}` (`review_gate`) để web tắt nút Duyệt.
  Lúc chạy thật, "khớp kỳ vọng" = test độc lập của Testgen + đối soát số dòng + kiểu cột; đáp án cố định chỉ có ở eval.

## Hợp đồng (chỉ thêm trường tùy chọn, checkpoint cũ vẫn đọc được)

`SandboxResult.dbt_invocation/model_timings/wall_ms`, `ModelTiming`, `OptimizationReport.bottlenecks` (`PerfReport`, `Bottleneck`).
`QueryMetrics.spread_ms` (IQR = Q3 − Q1, `statistics.quantiles(n=4, method="inclusive")`, cần ≥ 2 lần đo), `GateCheck`,
`ReviewGate`; API thêm `review_gate`, `reviews`. Không đổi tên node, không thêm khóa state.

## Kết luận nhanh hơn

Chỉ `applied` khi đạt `OPT_MIN_GAIN_PCT` **và** có IQR của cả bản gốc lẫn bản sửa **và** chênh lệch trung vị lớn hơn IQR lớn
nhất của hai bên. Thiếu IQR hoặc chênh trong độ phân tán → `skipped` (giữ bản gốc, ghi lý do).

## Bổ sung (2026-10-18, sau đánh giá)

- Bản gốc và bản sửa đo **xen kẽ A/B trên cùng kết nối, cùng thời điểm** (`benchmark_pair`); quyết định dùng cặp số đo này,
  không dùng số đo bản gốc của lượt đầu (eval cho thấy máy trôi 5–20% giữa các lượt, lớn hơn IQR).
- Giả định dữ liệu của luật đã áp dụng (khóa duy nhất, không trùng dòng, hai nhánh UNION không giao nhau) được ghi thành dbt test
  `tests/assert_opt_assumption_<n>.sql` trong `code_files`: chạy ở V2 và mỗi lần pipeline chạy thật; `opt_revert` bỏ luôn test.
