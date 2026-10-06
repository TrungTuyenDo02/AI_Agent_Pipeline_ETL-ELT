# ADR 0003 — Kiểm chứng bằng code thuần; Testgen không thấy code của Coder

- Ngày: 2026-10-02 • Trạng thái: Chấp nhận

## Quyết định
- V0 (soát spec), V1 (an toàn, sqlglot), V2 (dbt build trong sandbox DuckDB), V3 (đối chiếu kết quả hai chiều trên
  5 bộ dữ liệu) là code tất định; không hỏi LLM "đúng chưa" hay "hai query có tương đương không".
- Testgen chỉ nhận spec + danh mục + hồ sơ dữ liệu (`blind_inputs`), có test kiểm chứng điều này.
- Bằng chứng gửi Reviewer tách `measured` (code đo) và `claimed` (LLM nói).

## Hệ quả
- Test đối soát độc lập đã bắt được lỗi giả SUM→AVG (test `test_sandbox_catches_wrong_aggregation`).
- Optimizer có thể ra `skipped` (lợi ích < `OPT_MIN_GAIN_PCT`, đề xuất giống bản gốc, kết quả lệch) — là kết quả hợp lệ.
