# ADR 0018 — Optimizer dùng báo cáo điểm nghẽn làm tín hiệu bổ sung

- Ngày: 2026-10-18 • Trạng thái: đã chấp nhận (chủ dự án đồng ý)

## Quyết định

Khi sqlglot không thấy mẫu đáng nghi, optimizer không bỏ qua ngay mà xét bằng chứng thực thi (V, 0 token):

1. Báo cáo V2 phải khớp: model đích nằm trong top `PERF_TOP_N` theo `execute_ms`, và `source_sha` (sha256 của SQL gốc dbt đã
   chạy, chuẩn hóa xuống dòng, lưu trong `target/runs/<invocation_id>.json`) bằng SQL hiện tại của model.
2. `EXPLAIN ANALYZE` đúng SQL sẽ tối ưu trên đúng bộ dữ liệu sẽ đo (`large`), chạy ≥ `OPT_SIGNAL_MIN_MS` (mặc định 100 ms) và có
   mẫu cụ thể: nối không theo điều kiện bằng chiếm ≥ 30% thời gian toán tử (`exec_non_equi_join`), hoặc nối ra ≥ 2 lần đầu vào
   (`exec_join_fanout`, chỉ là dấu hiệu cần điều tra: không thêm DISTINCT, không bỏ dòng).
3. Thiếu, lệch hoặc lỗi ở bất kỳ bước nào → giữ luồng cũ (`skipped`).

Thứ tự luật → sqlglot → LLM và mọi kiểm chứng (V1 an toàn, V3 đối chiếu 6 bộ + IQR, V2 so lại sandbox) giữ nguyên. Không đổi tên
node, không thêm khóa state; `OptimizeJob.signals` (tùy chọn) cho lệnh chạy riêng và eval.
