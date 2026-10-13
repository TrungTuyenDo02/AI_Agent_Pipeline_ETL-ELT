# Baseline TPC-H: truy vấn viết tay không tối ưu = 100%

- Ngày đo: 2026-10-14 • sf=0.1 • DuckDB local • trung vị 7 lần (sau 1 lần khởi động) • 1 lần chạy cả bộ.
- Mốc 100% = truy vấn chậm viết tay (`eval/benchmarks/tpch/slow/`). Cột "Sau" = % so với mốc, tối ưu bằng luật cố định + sqlglot (LLM mô phỏng, 0 token).
- Chi phí ước tính/tháng = giây × 30 lần/tháng × 0.5 USD/giờ tính toán (**giả định**, không phải hóa đơn).
- "Dữ liệu quét" = số dòng DuckDB đọc từ bảng. Số byte đọc từ đĩa (`total_bytes_read`) luôn bằng 0 vì DuckDB local đã đọc sẵn vào bộ nhớ, nên KHÔNG dùng làm số đo (chỉ lưu trong JSON).

| Query | Quyết định | Thời gian trước (ms) | Sau | Dòng quét trước | Sau | Chi phí/tháng trước (USD) | Sau |
|---|---|---|---|---|---|---|---|
| q01_distinct_star | applied | 183.906 | 6% | 600,572 | 100% | 0.000766 | 6% |
| q01_order_in_subquery | applied | 169.936 | 8% | 600,572 | 100% | 0.000708 | 8% |
| q01_union_select_star | applied | 175.864 | 13% | 1,201,144 | 100% | 0.000733 | 13% |
| q01_window_dedupe | applied | 128.326 | 11% | 600,572 | 100% | 0.000535 | 11% |
| q03_cast_join | skipped | 19.604 | 100% | 765,572 | 100% | 8.2e-05 | 100% |
| q03_filter_after_join | applied | 24.263 | 71% | 765,572 | 100% | 0.000101 | 70% |
| q03_order_in_subquery | applied | 93.288 | 19% | 765,572 | 100% | 0.000389 | 19% |
| q05_range_join | applied | 297.522 | 7% | 766,602 | 100% | 0.00124 | 7% |
| q09_distinct_star | applied | 203.329 | 16% | 851,597 | 100% | 0.000847 | 16% |
| q09_window_dedupe | applied | 126.905 | 24% | 1,452,169 | 59% | 0.000529 | 24% |
| q15_repeated_subquery | skipped | 6.049 | 100% | 601,572 | 100% | 2.5e-05 | 100% |
| q18_union_subquery | applied | 334.099 | 11% | 1,598,076 | 62% | 0.001392 | 11% |
| q21_union_lineitem | applied | 320.113 | 13% | 2,553,313 | 76% | 0.001334 | 13% |
| **Tổng** | | 2083.2 | 14% | 13,122,905 | 86% | 0.00868 | 14% |

Giới hạn: dữ liệu TPC-H nhỏ (sf 0,1) nên tiền tuyệt đối rất nhỏ, chỉ tỉ lệ có ý nghĩa; mỗi truy vấn đo một lần chạy; chưa so với DE làm tay (xem PROTOCOL.md) và chưa chạy trên kho dữ liệu đám mây thật.
