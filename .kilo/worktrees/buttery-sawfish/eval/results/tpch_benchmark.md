# Benchmark TPC-H — Optimizer (E4) + Đối chiếu (V3)

- Ngày đo: 2026-10-02 • scale factor: 0.1 • provider/model: mock/mock
- Ngưỡng áp dụng: nhanh hơn ≥ 15.0% và kết quả giống hệt; trung vị của 5 lần đo.

| Query | Query chậm đúng đáp án | Quyết định | Nguồn đề xuất | Trước (ms) | Sau (ms) | Cải thiện | Gọi LLM |
|---|---|---|---|---|---|---|---|
| q01_distinct_star | ✓ | applied | rules | 263.854 | 26.517 | 90.0% | 0 |
| q01_order_in_subquery | ✓ | applied | rules | 322.015 | 19.337 | 94.0% | 0 |
| q01_union_select_star | ✓ | applied | rules | 256.105 | 25.457 | 90.1% | 0 |
| q01_window_dedupe | ✓ | applied | rules | 165.918 | 12.961 | 92.2% | 0 |
| q03_cast_join | ✓ | skipped | llm | 19.154 | — | — | 1 |
| q03_filter_after_join | ✓ | applied | sqlglot | 42.775 | 20.955 | 51.0% | 0 |
| q03_order_in_subquery | ✓ | applied | rules | 150.291 | 23.809 | 84.2% | 0 |
| q05_range_join | ✓ | applied | rules | 563.495 | 29.614 | 94.7% | 0 |
| q09_distinct_star | ✓ | applied | rules | 269.723 | 45.871 | 83.0% | 0 |
| q09_window_dedupe | ✓ | applied | rules | 159.135 | 38.368 | 75.9% | 0 |
| q15_repeated_subquery | ✓ | skipped | llm | 8.01 | — | — | 2 |
| q18_union_subquery | ✓ | applied | rules | 434.64 | 38.175 | 91.2% | 0 |
| q21_union_lineitem | ✓ | applied | rules | 390.118 | 46.564 | 88.1% | 0 |
