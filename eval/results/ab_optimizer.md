# A/B model cho Optimizer (E4) trên TPC-H

- Ngày đo: 2026-10-14 • sf=0.1 • tối đa 2 lần thử/query • trung vị 5 lần đo • **chỉ ứng viên do LLM viết** (bỏ luật cố định và sqlglot) • mỗi cấu hình chạy 1 lần.
- "Bản đúng và nhanh hơn ngưỡng" = qua V3 (kết quả giống hệt) và nhanh hơn ≥ 15%. "Áp dụng" còn phải qua cổng chi phí (tiết kiệm/năm > chi phí gọi LLM); trên TPC-H nhỏ cổng này loại nhiều ca dù bản viết lại tốt. Chi phí = số token thật × bảng giá trong src/services/cost.py.

| Model | Bản đúng và nhanh hơn ngưỡng | Áp dụng (qua cổng chi phí) | Cải thiện trung vị | Số lần gọi LLM | Tổng chi phí (USD) |
|---|---|---|---|---|---|
| anthropic:claude-opus-5-5:medium | 3/13 | 0/13 | 45.8% | 26 | 0.957 |
| openai:gpt-5.6-terra | 5/13 | 2/13 | 52.0% | 24 | 0.2373 |

## Từng query

| Query | anthropic:claude-opus-5-5:medium | openai:gpt-5.6-terra |
|---|---|---|
| q01_distinct_star | skipped (40.7%) | skipped |
| q01_order_in_subquery | skipped | applied (92.1%) |
| q01_union_select_star | skipped | skipped |
| q01_window_dedupe | skipped (-70.4%) | skipped |
| q03_cast_join | skipped | skipped |
| q03_filter_after_join | skipped | skipped (25.7%) |
| q03_order_in_subquery | skipped | skipped |
| q05_range_join | skipped | applied (93.0%) |
| q09_distinct_star | skipped | skipped |
| q09_window_dedupe | skipped (45.8%) | skipped |
| q15_repeated_subquery | skipped | skipped |
| q18_union_subquery | skipped (90.5%) | skipped (36.9%) |
| q21_union_lineitem | skipped | skipped (52.0%) |

Giới hạn: 1 lần chạy mỗi model, chưa lặp lại; thời gian query dao động giữa các lần đo; chỉ 13 query TPC-H, chưa phản ánh query thật của doanh nghiệp.
