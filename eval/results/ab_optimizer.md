# A/B model cho Optimizer (E4) trên TPC-H

- Ngày đo: 2026-10-14 • sf=0.1 • tối đa 2 lần thử/query • trung vị 5 lần đo • **chỉ ứng viên do LLM viết** (bỏ luật cố định và sqlglot) • mỗi cấu hình chạy 1 lần.
- "Bản đúng và nhanh hơn ngưỡng" = qua V3 (kết quả giống hệt) và nhanh hơn ≥ 15%. "Áp dụng" còn phải qua cổng chi phí (tiết kiệm/năm > chi phí gọi LLM); trên TPC-H nhỏ cổng này loại nhiều ca dù bản viết lại tốt. Chi phí = số token thật × bảng giá trong src/services/cost.py.

| Model | Bản đúng và nhanh hơn ngưỡng | Áp dụng (qua cổng chi phí) | Cải thiện trung vị | Số lần gọi LLM | Tổng chi phí (USD) |
|---|---|---|---|---|---|
| anthropic:claude-opus-5-5:medium | 3/13 | 0/13 | 45.8% | 26 | 0.957 |
| openai:gpt-5.6-terra | 5/13 | 2/13 | 52.0% | 24 | 0.2373 |
| anthropic:claude-haiku-4-5-20251001 | 11/13 | 8/13 | 89.6% | 18 | 0.0834 |
| anthropic:claude-haiku-5-5 | 9/13 | 7/13 | 42.8% | 20 | 0.0248 |

## Từng query

| Query | anthropic:claude-opus-5-5:medium | openai:gpt-5.6-terra | anthropic:claude-haiku-4-5-20251001 | anthropic:claude-haiku-5-5 |
|---|---|---|---|---|
| q01_distinct_star | skipped (40.7%) | skipped | applied (93.3%) | skipped |
| q01_order_in_subquery | skipped | applied (92.1%) | applied (92.5%) | applied (91.4%) |
| q01_union_select_star | skipped | skipped | applied (92.3%) | applied (16.4%) |
| q01_window_dedupe | skipped (-70.4%) | skipped | applied (89.6%) | skipped |
| q03_cast_join | skipped | skipped | skipped (11.3%) | skipped (16.0%) |
| q03_filter_after_join | skipped | skipped (25.7%) | skipped (31.8%) | skipped (22.6%) |
| q03_order_in_subquery | skipped | skipped | skipped (82.0%) | applied (80.5%) |
| q05_range_join | skipped | applied (93.0%) | applied (92.3%) | applied (93.1%) |
| q09_distinct_star | skipped | skipped | applied (82.7%) | applied (35.5%) |
| q09_window_dedupe | skipped (45.8%) | skipped | skipped (76.3%) | skipped |
| q15_repeated_subquery | skipped | skipped | skipped (2.2%) | skipped (12.6%) |
| q18_union_subquery | skipped (90.5%) | skipped (36.9%) | applied (93.4%) | applied (42.8%) |
| q21_union_lineitem | skipped | skipped (52.0%) | applied (87.6%) | applied (51.3%) |

Giới hạn: 1 lần chạy mỗi model, chưa lặp lại; thời gian query dao động giữa các lần đo; chỉ 13 query TPC-H, chưa phản ánh query thật của doanh nghiệp.
