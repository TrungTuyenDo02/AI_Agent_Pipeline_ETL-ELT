# Đánh giá Extract

- Dataset: `p113-extract-v1`; dữ liệu tổng hợp, oracle cố định độc lập.
- Đạt **21/21** (100.0%); nghiệm thu: **đạt**.
- Gọi connector, sổ nguồn và hàm nạp thật trong tiến trình/SQLite tạm riêng; 0 LLM, không mạng.
- Thời gian harness gồm dựng fixture và kiểm tra: 3.737 giây; không đại diện độ trễ sản phẩm.
- Điểm chỉ cho phạm vi đã chạy; mọi ca phải qua, lỗi quyền/nguồn không được bù bằng điểm khác.
- Chưa đánh giá: PostgreSQL thật, kiểu native phức tạp và múi giờ, API đối tác, CDC/incremental, lựa chọn nguồn tự động khi trùng tên bảng.

| Ca | Nhóm | Đạt | Thời gian (s) |
|---|---|---|---|
| `csv_exact` | exact_extract | đạt | 0.1743 |
| `json_exact` | exact_extract | đạt | 0.1042 |
| `same_name_other_department` | exact_extract | đạt | 0.1404 |
| `sqlite_exact` | exact_extract | đạt | 0.1219 |
| `duckdb_exact` | exact_extract | đạt | 0.1727 |
| `schema_qualified_table` | exact_extract | đạt | 0.1654 |
| `empty_table_schema` | exact_extract | đạt | 0.1709 |
| `parquet_exact` | exact_extract | đạt | 0.1073 |
| `column_added` | exact_extract | đạt | 0.1241 |
| `column_renamed` | exact_extract | đạt | 0.1197 |
| `column_removed` | exact_extract | đạt | 0.1164 |
| `sampling_repeatable_subset` | sampling | đạt | 0.1874 |
| `forbidden_table` | access | đạt | 0.0223 |
| `department_visibility` | access | đạt | 0.0032 |
| `cross_department_ingest` | access | đạt | 0.0621 |
| `revoked_source_ingest` | access | đạt | 0.0633 |
| `changed_file_changes_output` | provenance | đạt | 0.2411 |
| `hashed_join` | privacy | đạt | 0.0912 |
| `missing_secret` | access | đạt | 0.0013 |
| `source_immutability` | provenance | đạt | 0.0089 |
| `scorer_negative_controls` | scorer | đạt | 0.0008 |

## Bằng chứng nguồn

Mã băm của file nguồn đã vật chất hóa, source_id và bảng được chọn; không ghi DSN, đường dẫn bí mật hoặc dòng dữ liệu vào báo cáo.
Mã băm xác nhận nội dung trong lần eval này; không phải chữ ký xác nhận nguồn ngoài thực tế.

| Ca | Source ID | Connector | File được đọc | Bảng | Dòng nạp | SHA-256 đầu vào |
|---|---|---|---|---|---|---|
| `csv_exact` | 2 | FileConnector | `partner_sales/orders.csv` | `orders` | 6 | `53c000001d6be563776d1101bd0520b0a1b7c7becc53bd8c5a1af53c5f1fdf17` |
| `json_exact` | 2 | FileConnector | `partner_sales/contacts.json` | `contacts` | 3 | `678c39511002c518e3db1043aa380056d9eb0b73a2dcb884608aeadcd7f7ceff` |
| `same_name_other_department` | 3 | FileConnector | `partner_finance/orders.csv` | `orders` | 6 | `942f90140ccdc817f46811f87e8ee5b6620bc30c6e4cb9742cc4abd98672543b` |
| `sqlite_exact` | 4 | FileConnector | `sqlite/warehouse.sqlite` | `warehouse_orders` | 4 | `d7cb9003ffb3a49a2451f937fff4f9b491758084a5fea739fa75a622a3c54e59` |
| `duckdb_exact` | 5 | DuckDBConnector | `warehouse.duckdb` | `orders` | 4 | `c7d2814148dd8cf74d8479d938711cea27914ac59a2c6d818037ebea309f17ec` |
| `schema_qualified_table` | 5 | DuckDBConnector | `warehouse.duckdb` | `ops__orders` | 1 | `c7d2814148dd8cf74d8479d938711cea27914ac59a2c6d818037ebea309f17ec` |
| `empty_table_schema` | 5 | DuckDBConnector | `warehouse.duckdb` | `empty_orders` | 0 | `c7d2814148dd8cf74d8479d938711cea27914ac59a2c6d818037ebea309f17ec` |
| `parquet_exact` | 6 | FileConnector | `parquet/orders.parquet` | `orders` | 4 | `0cb2611f00419f16b4a018e2ef210a07bc089ae033537d47dd4ea2664676c54a` |
| `column_added` | 7 | FileConnector | `added/orders.csv` | `orders` | 2 | `b1086645c95a484c3051d694f3ea49be2296d4caff409d73a437dd9e2bc3f9f0` |
| `column_renamed` | 8 | FileConnector | `renamed/orders.csv` | `orders` | 2 | `332a6e1f0f7986260f3af85dfaf441c04cb9af4408a9287329aab024a0e32692` |
| `column_removed` | 9 | FileConnector | `removed/orders.csv` | `orders` | 2 | `cfb9acb2164db80952cc8d7e4850d84f61cf2c8e03feb3b358ed3845d1b075fb` |
| `sampling_repeatable_subset` | 2 | FileConnector | `partner_sales/orders.csv` | `orders` | 3 | `53c000001d6be563776d1101bd0520b0a1b7c7becc53bd8c5a1af53c5f1fdf17` |
| `changed_file_changes_output` | 2 | FileConnector | `partner_sales/orders.csv` | `orders` | 6 | `3ce8a5545f2eb9a0364969bece5906c690355bf363bf16bc16d8dee8354aa0c8` |

Chi tiết schema, digest kết quả thực tế/đáp án và các phép kiểm tra nằm trong [extract.json](extract.json).

Ca `changed_file_changes_output` sửa bản sao đầu vào và đòi hỏi đầu ra đổi tương ứng; ca `scorer_negative_controls` kiểm tra sai nguồn cùng số dòng, sai dòng trùng và sai schema đều bị chấm trượt.
CSV giữ nguyên chuỗi ở raw (kể cả số 0 đầu, tiền dạng chuỗi); benchmark này chấm Extract, không chấm làm sạch hay khả năng suy luận của LLM.
