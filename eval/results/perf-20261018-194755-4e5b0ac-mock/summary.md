# Eval hiệu năng `perf-20261018-194755-4e5b0ac-mock`

- Provider: `mock` · commit `4e5b0ac` · 2026-10-18T19:47:55 · luồng đo DuckDB: 2 · 5 lần đo + 1 khởi động · ca perf 1,000,000 dòng
- Đúng kết quả kỳ vọng (đáp án đóng băng / truy vấn chuẩn TPC-H): **20/20**
- Đúng model + toán tử điểm nghẽn trong top 3: **6/6**
- Bản tối ưu được áp dụng: 15 · giữ kết quả bản gốc (tự kiểm lại): **15/15** · nhanh hơn vượt nhiễu: 15 · giữ nguyên: 5
- Chi phí LLM: 0 USD
- Độ ổn định (2 lượt): **kết quả chưa ổn định** (kết luận: giống nhau; thời gian: lệch quá ngưỡng nhiễu)
  - range_join: before_ms 1378.132→1292.873 (ngưỡng nhiễu 35.2 ms)
  - q01_distinct_star: before_ms 216.531→238.562 (ngưỡng nhiễu 11.928 ms)
  - q01_union_select_star: before_ms 238.285→207.232 (ngưỡng nhiễu 25.49 ms)
  - q01_window_dedupe: before_ms 179.307→151.824 (ngưỡng nhiễu 9.735 ms)
  - q03_cast_join: before_ms 27.658→22.126 (ngưỡng nhiễu 5.117 ms)
  - q03_filter_after_join: before_ms 28.113→23.134 (ngưỡng nhiễu 0.843 ms)
  - q03_order_in_subquery: before_ms 153.306→139.162 (ngưỡng nhiễu 10.272 ms)
  - q05_range_join: before_ms 562.175→491.254 (ngưỡng nhiễu 52.282 ms)
  - q09_distinct_star: before_ms 247.07→224.202 (ngưỡng nhiễu 15.096 ms)
  - q09_window_dedupe: before_ms 173.195→149.162 (ngưỡng nhiễu 14.548 ms)
  - q15_repeated_subquery: before_ms 8.933→7.236 (ngưỡng nhiễu 0.938 ms)
  - q18_union_subquery: before_ms 431.837→387.109 (ngưỡng nhiễu 44.428 ms)
  - q21_union_lineitem: before_ms 370.086→317.808 (ngưỡng nhiễu 18.355 ms)
- DAG do agent sinh (tỷ lệ qua lần đầu, qua đủ kiểm tra bắt buộc, số vòng sửa): không đánh giá năng lực LLM (LLM_PROVIDER=mock: code sinh tất định, tỷ lệ 100% không phải bằng chứng chất lượng)
- Nghiệm thu: **chưa đạt**

Phạm vi: "đúng trên bộ thử", "nhanh hơn trong môi trường đo" (sandbox DuckDB local). Thời gian toàn DAG: chưa đo.

| Ca | Loại | Đúng | Điểm nghẽn kỳ vọng | Top model:toán tử | Trúng | Quyết định | Giữ kết quả | Trước (IQR) ms | Sau (IQR) ms | Lợi % | Nhiễu % | Lý do |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| range_join | perf | đạt | m_band_revenue:PIECEWISE_MERGE_JOIN/IE_JOIN/NESTED_LOOP_JOIN/BLOCKWISE_NL_JOIN | m_band_revenue:PIECEWISE_MERGE_JOIN; m_city_list:HASH_GROUP_BY; m_status_count:HASH_GROUP_BY | đạt | skipped | — | 1292.873 (35.2) | chưa đo (chưa đo) | chưa đo | 2.4 | Không phát hiện dấu hiệu query chậm. |
| fanout_join | perf | đạt | m_city_revenue:HASH_JOIN/HASH_GROUP_BY | m_city_revenue:HASH_GROUP_BY; m_city_list:HASH_GROUP_BY; m_status_count:HASH_GROUP_BY | đạt | skipped | — | 505.269 (43.317) | chưa đo (chưa đo) | chưa đo | 5.9 | Không phát hiện dấu hiệu query chậm. |
| distinct_star | perf | đạt | m_status_orders:HASH_GROUP_BY | m_status_orders:HASH_GROUP_BY; m_status_count:HASH_GROUP_BY; m_city_list:HASH_GROUP_BY | đạt | skipped | — | 278.593 (7.792) | chưa đo (chưa đo) | chưa đo | 8.3 | Optimizer không đề xuất thay đổi nào an toàn; giữ nguyên bản gốc. |
| window_dedupe | perf | đạt | m_status_dedup:WINDOW/STREAMING_WINDOW/HASH_GROUP_BY | m_city_list:HASH_GROUP_BY; m_status_dedup:HASH_GROUP_BY; m_status_count:HASH_GROUP_BY | đạt | applied | đạt | 147.366 (20.844) | 5.542 (0.026) | 96.2 | 5.5 | Nhanh hơn 96.2% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| union_distinct | perf | đạt | m_status_union:HASH_GROUP_BY | m_city_list:HASH_GROUP_BY; m_status_union:HASH_GROUP_BY; m_status_count:HASH_GROUP_BY | đạt | applied | đạt | 139.414 (8.866) | 24.691 (2.479) | 82.3 | 7.5 | Nhanh hơn 82.3% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| order_in_subquery | perf | đạt | m_status_amount:ORDER_BY | m_city_list:HASH_GROUP_BY; m_status_amount:ORDER_BY; m_status_count:HASH_GROUP_BY | đạt | applied | đạt | 95.435 (2.117) | 7.662 (1.504) | 92.0 | 40.7 | Nhanh hơn 92.0% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| control_clean | perf | đạt | — | m_city_list:HASH_GROUP_BY; m_status_clean:HASH_GROUP_BY; m_status_count:HASH_GROUP_BY | — | skipped | — | 7.604 (0.114) | chưa đo (chưa đo) | chưa đo | 0.5 | Không phát hiện dấu hiệu query chậm. |
| q01_distinct_star | tpch | đạt | — |  | — | applied | đạt | 238.562 (6.692) | 25.121 (0.931) | 89.5 | 5.0 | Nhanh hơn 89.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q01_order_in_subquery | tpch | đạt | — |  | — | applied | đạt | 329.394 (11.728) | 16.752 (0.312) | 94.9 | 4.2 | Nhanh hơn 94.9% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q01_union_select_star | tpch | đạt | — |  | — | applied | đạt | 207.232 (7.68) | 24.763 (0.564) | 88.1 | 12.3 | Nhanh hơn 88.1% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q01_window_dedupe | tpch | đạt | — |  | — | applied | đạt | 151.824 (5.185) | 18.721 (2.427) | 87.7 | 1.1 | Nhanh hơn 87.7% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q03_cast_join | tpch | đạt | — |  | — | applied | đạt | 22.126 (1.177) | 16.488 (0.21) | 25.5 | 0.7 | Nhanh hơn 25.5% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q03_filter_after_join | tpch | đạt | — |  | — | applied | đạt | 23.134 (0.32) | 16.004 (0.254) | 30.8 | 2.5 | Nhanh hơn 30.8% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q03_order_in_subquery | tpch | đạt | — |  | — | applied | đạt | 139.162 (4.345) | 17.165 (0.509) | 87.7 | 0.9 | Nhanh hơn 87.7% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q05_range_join | tpch | đạt | — |  | — | applied | đạt | 491.254 (20.606) | 19.128 (0.156) | 96.1 | 0.6 | Nhanh hơn 96.1% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q09_distinct_star | tpch | đạt | — |  | — | applied | đạt | 224.202 (15.096) | 33.603 (1.898) | 85.0 | 1.7 | Nhanh hơn 85.0% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q09_window_dedupe | tpch | đạt | — |  | — | applied | đạt | 149.162 (9.66) | 32.525 (1.413) | 78.2 | 0.3 | Nhanh hơn 78.2% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q15_repeated_subquery | tpch | đạt | — |  | — | skipped | — | 7.236 (0.527) | chưa đo (chưa đo) | chưa đo | 1.7 | Optimizer không đề xuất thay đổi nào an toàn; giữ nguyên bản gốc. |
| q18_union_subquery | tpch | đạt | — |  | — | applied | đạt | 387.109 (1.843) | 30.075 (1.468) | 92.2 | 0.8 | Nhanh hơn 92.2% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
| q21_union_lineitem | tpch | đạt | — |  | — | applied | đạt | 317.808 (4.015) | 42.356 (0.304) | 86.7 | 0.5 | Nhanh hơn 86.7% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu. |
