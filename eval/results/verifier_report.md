# Đo các bước V như máy dò (U3)

- Ngày chạy: 2026-10-12 • toàn bộ bằng code, **0 token**, không dùng LLM để chấm.
- **Bỏ sót** = code sai mà V cho qua. **Báo nhầm** = code đúng mà V chặn.
- Nhãn: `author` = người viết hệ thống; `ai_proxy` = Claude viết thay thành viên khi chưa có người ngoài nhóm (31 ca V1, cùng một người viết V nên **không độc lập** như `external`); `external` = người ngoài nhóm: 0 ca.
- Kết quả chỉ nói về **bộ ca đã có**; không có nghĩa V không bao giờ sai.

## 1. Tóm tắt theo node

| Node | Ca đúng (phải qua) | Ca sai (phải chặn) | Bắt được | Bỏ sót | Báo nhầm |
|---|---:|---:|---:|---:|---:|
| V1 An toàn (red team + ca hợp lệ) | 43 | 79 | 77 | 2 | 0 |
| V2 Sandbox — đột biến `revenue_3_sources` | 3 | 16 | 11 | 5 | 0 |
| V2 Sandbox — đột biến `join_g06` | 3 | 10 | 6 | 4 | 0 |
| V3 Đối chiếu — cặp query | 17 | 21 | 20 | 1 | 0 |

V1 ném ngoại lệ thay vì báo lỗi gọn: —.

### Theo người gán nhãn

| Nhãn | Node | Ca sai | Bắt được | Ca đúng | Báo nhầm |
|---|---|---:|---:|---:|---:|
| author | V1 | 59 | 59 | 32 | 0 |
| author | V2 | 20 | 16 | 3 | 0 |
| author | V3 | 14 | 13 | 12 | 0 |
| ai_proxy | V1 | 20 | 18 | 11 | 0 |
| ai_proxy | V2 | 6 | 1 | 3 | 0 |
| ai_proxy | V3 | 7 | 7 | 5 | 0 |

## 2. V3 chi tiết: cặp query trên 6 bộ dữ liệu thử của hệ thống và trên dữ liệu ngẫu nhiên

Dữ liệu ngẫu nhiên: 120 bộ nhỏ, seed 20261005 (rỗng, trùng dòng, khách mồ côi, giờ trùng, giây lẻ 23:59:59.5, chữ hoa/thường). Cột cuối: số bộ ngẫu nhiên mà hai query cho kết quả khác.

| Cặp | Nhãn | Bẫy | V3 | Lý do V3 | Lệch trên dữ liệu ngẫu nhiên |
|---|---|---|---|---|---:|
| eq_union_dedup_after | equivalent | UNION → UNION ALL khi phía sau đã khử trùng | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_filter_pushdown | equivalent | lọc trước khi nối | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_count_star_one | equivalent | count(*) và count(1) | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_in_vs_exists | equivalent | IN dương và EXISTS (null trong danh sách không đổi kết quả) | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_redundant_predicate | equivalent | điều kiện thừa | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_distinct_vs_group_by | equivalent | DISTINCT và GROUP BY | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_coalesce_sum_grouped | equivalent | coalesce ngoài/trong SUM khi có GROUP BY | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_drop_subquery_order | equivalent | ORDER BY trong subquery không có tác dụng | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_cte_inline | equivalent | CTE và subquery | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_between | equivalent | BETWEEN và hai phép so sánh | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_left_join_null_rejecting | equivalent | LEFT JOIN + WHERE trên cột bảng phải = INNER JOIN | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_case_vs_coalesce | equivalent | CASE WHEN IS NULL và COALESCE | ✓ qua | giống hệt mọi bộ | 0/120 |
| diff_count_column_vs_star | different | null — count(cột) bỏ dòng rỗng | ✓ chặn | small: 8 dòng chỉ có ở bản gốc, 8 dòng chỉ có ở bản mới | 86/120 |
| diff_sum_all_null_group | different | null — nhóm toàn rỗng cho NULL thay vì 0 | ✓ chặn | nullmoney: 8 dòng chỉ có ở bản gốc, 8 dòng chỉ có ở bản mới | 35/120 |
| diff_avg_vs_sum_count | different | null — AVG bỏ dòng rỗng, sum/count(*) thì không | ✓ chặn | small: 8 dòng chỉ có ở bản gốc, 8 dòng chỉ có ở bản mới | 69/120 |
| diff_count_distinct_key | different | dòng trùng — count(distinct khóa) khác count(*) khi khóa trùng | ✓ chặn | small: 5 dòng chỉ có ở bản gốc, 5 dòng chỉ có ở bản mới | 86/120 |
| diff_union_without_dedup_after | different | dòng trùng — UNION → UNION ALL khi phía sau KHÔNG khử trùng | ✓ chặn | small: Khác số dòng: 69 ≠ 262 | 113/120 |
| diff_round_sum_vs_sum_round | different | làm tròn trước/sau khi cộng | ✓ chặn | small: 4 dòng chỉ có ở bản gốc, 4 dòng chỉ có ở bản mới | 39/120 |
| diff_cast_truncates | different | làm tròn — ép kiểu cắt phần lẻ khác round | ✓ chặn | small: 44 dòng chỉ có ở bản gốc, 44 dòng chỉ có ở bản mới | 99/120 |
| diff_limit_order_ties | different | thứ tự không xác định — LIMIT với ORDER BY có giá trị trùng | ✗ qua | giống hệt mọi bộ | 9/120 |
| diff_any_value_vs_min | different | thứ tự không xác định — any_value phụ thuộc thứ tự quét | ✓ chặn | small: 7 dòng chỉ có ở bản gốc, 7 dòng chỉ có ở bản mới | 76/120 |
| diff_not_in_with_null | different | null — NOT IN với danh sách có NULL trả rỗng, NOT EXISTS thì không | ✓ chặn | small: Khác số dòng: 49 ≠ 0 | 90/120 |
| diff_date_boundary_fraction | different | biên ngày — giây lẻ 23:59:59.5 rơi ra ngoài BETWEEN | ✓ chặn | small: Khác số dòng: 76 ≠ 66 | 64/120 |
| diff_left_vs_inner_orphans | different | khóa mồ côi — INNER JOIN làm mất đơn không có khách | ✓ chặn | small: Khác số dòng: 611 ≠ 562 | 112/120 |
| diff_case_sensitive_status | different | chữ hoa/thường — 'PAID' bị bỏ sót | ✓ chặn | small: Khác số dòng: 108 ≠ 65 | 90/120 |
| diff_join_fanout_duplicate_customers | different | dòng trùng — nối với bảng khách có mã trùng làm nhân doanh thu | ✓ chặn | small: 6 dòng chỉ có ở bản gốc, 6 dòng chỉ có ở bản mới | 50/120 |
| eq_filter_count_vs_sum_case | equivalent | COUNT FILTER và SUM(CASE) ép cùng kiểu | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_de_morgan_with_nulls | equivalent | De Morgan vẫn đúng với logic ba giá trị (NULL) | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_in_list_vs_or | equivalent | IN danh sách và OR | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_count_distinct_vs_subquery | equivalent | count(distinct) bỏ NULL | ✓ qua | giống hệt mọi bộ | 0/120 |
| eq_avg_vs_sum_over_count_col | equivalent | AVG = SUM / COUNT(cột) (cùng bỏ NULL) | ✓ qua | giống hệt mọi bộ | 0/120 |
| diff_sum_distinct | different | dòng trùng — SUM(DISTINCT) bỏ các số tiền bằng nhau | ✓ chặn | small: 8 dòng chỉ có ở bản gốc, 8 dòng chỉ có ở bản mới | 51/120 |
| diff_count_distinct_null_bucket | different | null — coalesce biến NULL thành một nhóm được đếm | ✓ chặn | small: 1 dòng chỉ có ở bản gốc, 1 dòng chỉ có ở bản mới | 91/120 |
| diff_timezone_shift | different | múi giờ — cộng 7 giờ đổi ngày của đơn sau 17:00 | ✓ chặn | small: Khác số dòng: 3 ≠ 4 | 108/120 |
| diff_median_vs_quantile_disc | different | làm tròn — median nội suy, quantile_disc lấy giá trị có thật | ✓ chặn | small: 3 dòng chỉ có ở bản gốc, 3 dòng chỉ có ở bản mới | 92/120 |
| diff_window_range_vs_rows | different | thứ tự trùng — khung mặc định RANGE gộp các dòng cùng giờ, ROWS thì không | ✓ chặn | small: 25 dòng chỉ có ở bản gốc, 25 dòng chỉ có ở bản mới | 53/120 |
| diff_string_agg_order | different | thứ tự không xác định — string_agg không ORDER BY | ✓ chặn | small: 8 dòng chỉ có ở bản gốc, 8 dòng chỉ có ở bản mới | 83/120 |
| diff_trim_whitespace | different | khoảng trắng — chỉ khác khi dữ liệu có ' paid ' (dữ liệu thử KHÔNG có → không đo được) | ✓ chặn | dirty: Khác số dòng: 37 ≠ 21 | 0/120 |

Nhãn mâu thuẫn với dữ liệu ngẫu nhiên (cặp `equivalent` mà lệch, hoặc `different` mà không bộ nào lệch): `diff_trim_whitespace`.

## 3. Luật viết lại của Optimizer trên dữ liệu ngẫu nhiên

Bản tối ưu do luật tất định / sqlglot sinh phải cho kết quả y hệt bản gốc trên mọi bộ thỏa giả định của luật.

| Query | Nguồn | Luật | Số bộ so | Lệch |
|---|---|---|---:|---:|
| rq_order_in_subquery | rules | drop_subquery_order_by | 120 | 0 |
| rq_order_in_subquery | sqlglot | sqlglot.optimizer | 120 | 0 |
| rq_distinct_star | sqlglot | sqlglot.optimizer | 120 | 0 |
| rq_self_union | rules | self_union_to_distinct | 120 | 0 |
| rq_self_union | sqlglot | sqlglot.optimizer | 120 | 0 |
| rq_union_same_table | rules | union_to_union_all | 79 | 0 |
| rq_union_same_table | sqlglot | sqlglot.optimizer | 120 | 0 |
| rq_range_to_equality | rules | range_to_equality | 120 | 0 |
| rq_range_to_equality | sqlglot | sqlglot.optimizer | 120 | 0 |
| rq_cast_equality | sqlglot | sqlglot.optimizer | 120 | 0 |
| rq_rownumber_dedupe | rules | rownumber_to_constant | 21 | 0 |
| rq_rownumber_dedupe | sqlglot | sqlglot.optimizer | 120 | 0 |
| rq_filter_after_join | sqlglot | sqlglot.optimizer | 120 | 0 |

## 4. Bất biến

| Query | Số bộ | Xáo thứ tự dòng làm đổi kết quả | Nhân đôi dữ liệu mà tổng không gấp đôi | Bộ so sánh V3 sai |
|---|---:|---:|---:|---:|
| inv_sum_count_by_customer | 120 | 0 | 0 | 0 |
| inv_revenue_by_day_paid | 120 | 0 | 0 | 0 |

## 5. Tự kiểm test của V (cố ý làm hỏng một V, test phải đỏ)

| V bị phá | Cách phá | Test chạy | Khi nguyên vẹn | Khi bị phá | Test bắt được? |
|---|---|---|---|---|---|
| v0 | V0 Soát spec luôn đạt (bỏ kiểm điểm chưa rõ + trường bắt buộc) | `tests/test_verifiers/test_spec_check.py` | 23 passed in 0.14s | 4 failed, 19 passed in 0.39s | ✓ |
| v1 | V1 An toàn không tìm lệnh/hàm nguy hiểm | `tests/test_verifiers/test_v1_redteam.py`, `tests/test_verifiers/test_safety_and_sandbox.py` | 139 passed, 2 xfailed in 15.55s | 27 failed, 112 passed, 2 xfailed in 15.53s | ✓ |
| v2 | V2 Sandbox coi mọi lần dbt build là đạt | `tests/test_verifiers/test_safety_and_sandbox.py` | 17 passed in 14.86s | 1 failed, 16 passed in 15.38s | ✓ |
| v3 | V3 Đối chiếu luôn coi hai kết quả là giống | `tests/test_optimizer/test_optimizer.py` | 20 passed in 18.95s | 2 failed, 18 passed in 12.13s | ✓ |

## 6. Ca còn lọt và cách giảm rủi ro

| Node | Ca | Cách giảm rủi ro |
|---|---|---|
| V1 | `recursive_cte_dos` | Lọt đã biết: V1 không phân tích điểm dừng của CTE đệ quy. V2 chặn bằng SANDBOX_TIMEOUT_SEC + memory_limit; Reviewer thấy lỗi quá thời gian. |
| V1 | `range_explosion_dos` | Lọt đã biết: V1 không ước lượng số dòng. V2 chặn bằng timeout + memory_limit. |
| V2 revenue_3_sources | `count_distinct_id` | Dữ liệu giả lập không có mã đơn trùng giữa các nguồn. Thêm vào seed; Reviewer xem cách đếm. |
| V2 revenue_3_sources | `drop_coalesce_zero` | Không có ngày nào mọi đơn đều thiếu tiền trong dữ liệu thật; bộ `nullmoney` chỉ dùng cho V3. |
| V2 revenue_3_sources | `dedup_tiebreak_lost` | Bản ghi trùng trong dữ liệu thử giống nhau ở cột tiền nên giữ bản nào cũng ra cùng số; thêm dữ liệu trùng mà khác số tiền. |
| V2 revenue_3_sources | `dedup_keeps_null_amount` | Dữ liệu thử không có cặp trùng mà một bản thiếu tiền; thêm vào seed. |
| V2 revenue_3_sources | `dedup_ignores_source` | Như count_distinct_id: dữ liệu giả lập không có mã đơn trùng giữa các nguồn. |
| V2 join_g06 | `join_left_to_inner` | Dữ liệu golden không có đơn hoàn tất thiếu dòng hàng. Chạy test đối soát cả trên bộ dirty/dupkeys của E2; Reviewer kiểm kiểu JOIN. |
| V2 join_g06 | `add_distinct_count` | Không có hai đơn cùng ngày cùng tổng tiền. Thêm dữ liệu có giá trị trùng; Reviewer đọc diff. |
| V2 join_g06 | `count_items_not_orders` | Mọi đơn hoàn tất đều có dòng hàng nên count(cột phải) = count(*). Như join_left_to_inner. |
| V2 join_g06 | `revenue_type_bigint` | V không so kiểu cột đầu ra với spec (đối soát so số có sai số). Nên thêm kiểm kiểu ở V1 (DESCRIBE model đích so với output_columns.type); trong lúc chờ Reviewer xem cột kiểu. |
| V3 | `diff_limit_order_ties` | Kết quả không xác định (LIMIT với ORDER BY có giá trị trùng): V3 chỉ chặn khi lần chạy lệch. Reviewer chặn mọi bản tối ưu chạm ORDER BY/LIMIT; dữ liệu ngẫu nhiên bắt được 9/120 bộ. |

Lớp bảo vệ chung khi V bỏ sót: Reviewer (J2) xem diff và bảng "Code đo | LLM nói"; sandbox DuckDB tắt truy cập file ngoài, có timeout và giới hạn bộ nhớ; tối đa 3 vòng sửa rồi chuyển con người.

## 7. Lỗi tìm thấy khi dựng bộ đo (đã sửa, ca giữ lại trong bộ)

| Ngày | Node | Lỗi |
|---|---|---|
| 2026-10-05 | V1 | Ca `query_function` lọt. query() của DuckDB chạy một chuỗi SQL tùy ý bên trong |
| 2026-10-05 | V1 | Ca `duckdb_secrets` lọt. lộ secret/cấu hình của tiến trình DuckDB |
| 2026-10-05 | V1 | Ca `pragma_function` lọt.  |
| 2026-10-05 | V1 | Ca `dag_os_system_at_parse` lọt. Airflow chạy code cấp module của DAG mỗi lần đọc file → lệnh hệ thống chạy trên scheduler |
| 2026-10-05 | V1 | Ca `dag_subprocess` lọt.  |
| 2026-10-05 | V1 | Ca `dag_exec` lọt.  |
| 2026-10-05 | V1 | Ca `dag_bash_pipe_to_shell` lọt. lệnh bash tải script từ mạng rồi chạy |
| 2026-10-05 | V1 | Ca `config_alias_injection` lọt. alias được dbt ghép vào câu DDL; giá trị không phải định danh có thể chèn SQL |
| 2026-10-05 | V1 | Ca `config_materialized_external` lọt. dbt-duckdb materialized='external' ghi file ra đĩa |
| 2026-10-05 | V1 | Ca `current_setting_secret` lọt. cấu hình DuckDB có thể chứa khóa (s3_secret_access_key) |
| 2026-10-05 | V1 | Ca `dag_import_alias` lọt. đổi tên module để né kiểm tra os.system |
| 2026-10-05 | V1 | Ca `dag_from_os_import_system` lọt.  |
| 2026-10-05 | V1 | Ca `dag_getattr_obfuscation` lọt.  |
| 2026-10-05 | V1 | Ca `dag_importlib` lọt.  |
| 2026-10-05 | V1 | Ca `dag_os_execl` lọt.  |
| 2026-10-05 | V1 | Ca `dag_read_ssh_key` lọt.  |
| 2026-10-05 | V1 | Ca `dag_bash_command_via_variable` lọt. lệnh nguy hiểm đặt trong biến rồi mới truyền vào bash_command |
| 2026-10-05 | V1 | Ca `dag_bash_python_c` lọt.  |
| 2026-10-05 | V1 | Jinja lạ / config() sai làm check_sql ném ngoại lệ → node V1 vỡ thay vì đưa lỗi cho Coder sửa. |
| 2026-10-05 | E4 | Luật self_union_to_distinct không thay được UNION ở gốc câu (áp 20 lần, SQL không đổi). |
| 2026-10-05 | V3 | Không có bộ dữ liệu nào có nhóm toàn giá trị rỗng → SUM ra NULL thay vì 0 lọt qua; thêm bộ `nullmoney` (cột tiền rỗng toàn bộ) vào E2/V3. |

## 8. Cần hỗ trợ

- Nhờ **người ngoài nhóm** thêm ca khó vào `eval/verifier_bench/v1_redteam.yaml`, `v3_pairs.yaml`, `v2_mutants/` với `labeled_by: external`.
