# Dataset Extract v1 — phòng ban và đối tác

Dữ liệu tổng hợp viết riêng cho P-113, không có dữ liệu cá nhân thật và không tải từ đối tác. Dataset nằm ngoài code connector. `expected.json` là đáp án được viết và đóng băng riêng; evaluator không sinh lại đáp án từ kết quả Extract.

Chạy riêng, không LLM và không mạng:

```powershell
python scripts/tasks.py eval-extract
# tương đương:
python eval/run_extract.py
```

Kết quả: [extract.md](../../results/extract.md) và [extract.json](../../results/extract.json). CLI trả mã 1 nếu có bất kỳ ca nào trượt; điểm cao ở ca khác không bù được lỗi quyền hoặc sai nguồn. `python eval/run_eval.py` cũng chạy bộ này và đưa điểm vào báo cáo chung.

## Dữ liệu có gì?

| Nguồn | Dữ liệu vật lý | Đáp án trong expected.json | Điều cần chứng minh |
|---|---|---|---|
| Đối tác của Kinh doanh | `sources/partner_sales/orders.csv` | `sales_orders` | 6 dòng, giữ dòng trùng, số dạng chuỗi, NULL, tiếng Việt, dấu phẩy/nháy/xuống dòng trong ô |
| Đối tác của Tài chính | `sources/partner_finance/orders.csv` | `finance_orders` | Cũng tên `orders`, cùng schema và 6 dòng nhưng nội dung khác; đếm dòng đúng chưa đủ |
| Danh bạ đối tác | `sources/partner_sales/contacts.json` | `contacts` | Đọc JSON, giữ NULL và kiểu số nguyên |
| Kho nội bộ | `native_tables.json` | `native_orders`, `ops_orders`, `empty_orders` | Vật chất hóa thành DuckDB/SQLite/Parquet thật ở thư mục tạm; kiểm kiểu, bảng rỗng và schema `ops` |
| Các phiên bản cấu trúc | `sources/added`, `sources/renamed`, `sources/removed` | `added`, `renamed`, `removed` | Schema được lấy từ nguồn hiện có, không hardcode tên cột cũ |
| Bảng ngoài quyền | `sources/partner_sales/private_payroll.json`, `private_payroll.sqlite` | Không được nạp | JSON/SQLite cố ý sai định dạng: discovery được cấp quyền `orders/contacts` phải bỏ qua trước khi parse |

Ba ca thêm/đổi tên/bớt cột chỉ chấm Extract lấy đúng cấu trúc hiện tại; việc phân loại schema drift và vá pipeline do các bộ test riêng kiểm tra.

Các bản DuckDB/SQLite/Parquet có chung blueprint, dùng để đối chiếu cùng dữ liệu qua các định dạng; đây không phải ba bộ dữ liệu độc lập của ba tổ chức thật.

## Chấm và chứng minh nguồn

- 11 ca đối chiếu chính xác: tên/thứ tự/kiểu cột, số dòng và từng dòng với số lần xuất hiện; thứ tự các dòng không ảnh hưởng điểm.
- 10 ca bổ sung: lấy mẫu lặp lại và đúng tập nguồn, chặn bảng ngoài quyền, quyền phòng ban, chặn nạp chéo phòng, nguồn bị tắt sau lúc lập danh mục, sửa file làm đầu ra đổi, băm giữ JOIN/NULL, thiếu secret không fallback, nguồn không bị sửa, và phản chứng bộ chấm.
- Luồng dùng sổ nguồn, connector và `_load` thật; tiến trình con luôn đặt DB ứng dụng/secret/lưu trữ về dữ liệu tạm riêng, không dùng DB dev/prod.
- Receipt có `source_id`, tên nguồn, phòng ban, connector, file tương đối, bảng, SHA-256 đầu vào, schema và số dòng nạp. JSON còn có digest đáp án/đầu ra và hash của mọi file fixture/oracle.
- Không đưa dòng dữ liệu, DSN hay đường dẫn bí mật vào báo cáo. Native DB được dựng từ blueprint ở thư mục tạm rồi xóa; hash blueprint cho phép kiểm lại nội dung nguồn, hash DB vật lý chỉ áp dụng cho lần chạy đó.
- Ca sửa đầu vào đổi `125000` thành `125001` ở bản sao nguồn và đòi hỏi đầu ra đổi tương ứng. Test riêng còn thay sai giá trị hoặc tráo file của phòng khác nhưng giữ nguyên oracle: benchmark phải trả mã 1.
- CSV giữ chuỗi ở raw, kể cả `00125.50`; chuyển tiền sang số là công việc Transform, không được trộn vào điểm Extract.

## Giới hạn

Điểm 100% chỉ có nghĩa toàn bộ ca trong bộ nhỏ này đạt. Chưa phủ mọi kiểu native phức tạp hay múi giờ; chưa đo PostgreSQL thật, API đối tác, CDC/incremental, nguồn lớn, độ ổn định khi nguồn đổi trong lúc đọc, hay lựa chọn nguồn tự động khi hai nguồn cùng tên bảng. Các ca trùng tên ở đây chọn `source_id` tường minh.

Receipt là bằng chứng cho lần eval trên fixture, không phải chữ ký xác thực dữ liệu do đối tác phát hành. Ứng dụng hiện có audit nguồn/bảng và số dòng; bản cập nhật này chưa thêm receipt bất biến cho từng run vào API/giao diện.

Muốn mở rộng: thêm file nguồn và oracle được kiểm riêng, đặt version mới cho thay đổi làm đổi đáp án, thêm ca vào `manifest.json`; không sửa đáp án chỉ để tăng điểm. Test của bộ chấm nằm ở [test_extract_benchmark.py](../../../tests/test_eval/test_extract_benchmark.py).
