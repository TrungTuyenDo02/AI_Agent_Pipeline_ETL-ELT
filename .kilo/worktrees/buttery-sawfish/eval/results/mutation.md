# Mutation test — bộ kiểm chứng có bắt được lỗi giả không?

- Ngày chạy: 2026-10-02 • mock (pipeline gốc tất định; không dùng LLM để chấm)
- Pipeline gốc: gộp 3 nguồn, doanh thu ngày (dữ liệu giả lập, seed 42). Kiểm chứng: V1 An toàn + V2 dbt build/test.

**Bắt được 11/12 lỗi giả (91.7%)**; báo động nhầm ở đột biến đối chứng: 0/1.

| Đột biến | Mô tả | Đối chứng | Bị bắt | Bắt bởi | Chi tiết |
|---|---|---|---|---|---|
| sum_to_avg | Đổi SUM → AVG khi tính doanh thu |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 30 results, configured to fail if != 0 |
| drop_where | Bỏ WHERE lọc trạng thái (tính cả đơn hủy/hoàn) |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 27 results, configured to fail if != 0 |
| widen_filter | Lọc sai trạng thái (tính cả đơn hoàn tiền) |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 20 results, configured to fail if != 0 |
| drop_dedup | Bỏ khử trùng đơn (tương đương bỏ DISTINCT) — bỏ cả hai lớp UNION và QUALIFY |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 5 results, configured to fail if != 0 |
| swap_columns | Đổi chỗ hai cột (số đơn ↔ doanh thu) |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 30 results, configured to fail if != 0 |
| count_distinct_id | Đếm đơn theo mã không kèm nguồn (chỉ sai khi có mã trùng giữa các nguồn) |  | ✗ | — | 3/3 test đạt |
| count_non_null | Đếm đơn bằng count(cột tiền) — bỏ sót đơn thiếu số tiền |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 2 results, configured to fail if != 0 |
| drop_source | Quên một nguồn khi gộp (bỏ website) |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 30 results, configured to fail if != 0 |
| date_format_swap | Đọc ngày sai định dạng (dd/mm ↔ mm/dd) |  | ✓ | V2: assert_fct_daily_revenue_reconciles, not_null_fct_daily_revenue_order_date.b774bf86f4 | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 37 results, configured to fail if != 0 |
| money_parse_bug | Không bỏ dấu chấm ở số tiền "1.075.000" |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 27 results, configured to fail if != 0 |
| date_shift | Lệch ngày một ngày (sai múi giờ) |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 31 results, configured to fail if != 0 |
| status_mapping_bug | Ánh xạ trạng thái sai ('paid' không được coi là hoàn tất) |  | ✓ | V2: assert_fct_daily_revenue_reconciles | test.p113_pipeline.assert_fct_daily_revenue_reconciles [fail]: Got 30 results, configured to fail if != 0 |
| union_all_control | Đối chứng: UNION → UNION ALL (bước khử trùng phía sau vẫn xử lý trùng, kết quả không đổi) | có | ✗ | — | 3/3 test đạt |
