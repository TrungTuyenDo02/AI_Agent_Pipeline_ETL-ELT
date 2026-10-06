HƯỚNG DẪN ĐỌC BẰNG CHỨNG KIỂM THỬ THỦ CÔNG — P-113
======================================================================

PHẦN 01 — ĐỌC FILE NÀO TRƯỚC?
======================================================================
Mỗi ca có một file TXT và các ảnh trong thư mục evidence/.
Các báo cáo ghi nhận lần chạy của người kiểm thử, không tự dựng output.

TC-01 | Chi phí quảng cáo VND
File: TC-01-ad-spend.txt
Kết quả: sandbox đạt 4/4 test, bảng 115 dòng. Ảnh còn ở trạng thái đang
chạy; chưa có bằng chứng hoàn tất toàn bộ luồng.

TC-02 | Doanh thu theo ngày và nguồn Shopee/Tiki
File: TC-02-daily-revenue-by-source.txt
Kết quả: sandbox đạt 4/4 test, bảng 60 dòng; đã duyệt và hoàn tất.

TC-03 | Số đơn và giá trị trung bình theo tháng/nguồn
File: TC-03-monthly-orders-failed.txt
Kết quả: KHÔNG ĐẠT. Dừng tại V1 vì Jinja không được phép và ngoại lệ
không được xử lý. Chưa có output sandbox. Có ảnh, code và log lỗi thật.

TC-04 | Số khoản và tổng tiền hoàn trả theo ngày
File: TC-04-daily-refunds.txt
Kết quả: sandbox đạt 3/3 test, bảng 30 dòng; API xác nhận đã duyệt.

TC-05 | Đếm nhân viên theo cửa hàng và kiểm tra ETL loại PII
File: TC-05-employee-count-by-store.txt
Kết quả: sandbox đạt 3/3 test, bảng 25 dòng; đang chờ duyệt J2.
ĐẠT MỘT PHẦN: bảng raw vẫn có năm cột nhạy cảm, nên yêu cầu loại
PII trước khi nạp vào sandbox KHÔNG ĐẠT. Có bằng chứng tên cột thực tế.

Hiện có 5 ca được ghi nhận, gồm ca có output thành công và ca lỗi.
Trạng thái hoàn tất và phạm vi đạt được ghi riêng trong từng báo cáo.

======================================================================
PHẦN 02 — CÁCH ĐỌC MỖI BÁO CÁO
======================================================================
Đọc "ĐỌC NHANH" để biết ca thành công, thất bại hay còn thiếu bằng chứng.
Đọc "YÊU CẦU" để biết người kiểm thử muốn hệ thống làm gì.
Đọc "KẾT QUẢ MONG ĐỢI" để biết tiêu chí cần kiểm tra.
Đọc "CÁC BƯỚC/DIỄN BIẾN" để biết người dùng và agent đã làm gì theo thứ tự.
Đọc "KẾT QUẢ THỰC TẾ" để biết từng bước đạt hay dừng ở đâu.
Đọc "OUTPUT/LỖI" để thấy giá trị thực tế hoặc thông báo lỗi.
Đọc "ĐÁNH GIÁ/KẾT LUẬN" để biết phạm vi nào đã được xác nhận.
Mở các ảnh/tệp bằng chứng theo đường dẫn ở cuối báo cáo.

======================================================================
PHẦN 03 — GIẢI THÍCH TỪNG BƯỚC TRÊN GIAO DIỆN
======================================================================
1. E1 Lập kế hoạch
   Agent hiểu yêu cầu, chọn bảng nguồn và đề xuất phép biến đổi.

2. V0 Soát đặc tả; J1 Hỏi làm rõ khi cần
   Code kiểm tra yêu cầu đã đủ rõ chưa. Nếu thiếu quy tắc, agent hỏi
   người dùng rồi lập lại. Dấu đỏ V0 có thể là một điểm chưa rõ cần giải
   quyết, không tự đồng nghĩa toàn bộ ca thất bại.

3. J1b Duyệt kế hoạch — NGƯỜI DÙNG THAO TÁC
   Người dùng đọc nguồn, bộ lọc, cách tính, cách loại trùng và bảng đích;
   đồng ý hoặc ghi chú yêu cầu sửa trước khi agent sinh code.

4. E0 Nhận nguồn -> P Soi dữ liệu -> E2 Dữ liệu thử
   Hệ thống nạp nguồn, đọc cấu trúc và chuẩn bị các bộ dữ liệu kiểm tra.
   Việc tạo small/large/dirty/... chưa tự chứng minh tất cả bộ đều đạt.

5. E3 Sinh code -> E3b Sinh test
   Agent tạo model dbt, DAG và test. Dấu xanh ở đây xác nhận tạo file;
   việc thực thi đạt hay không được kiểm tra ở các bước tiếp theo.

6. V1 An toàn -> V2 Sandbox
   Kiểm tra lệnh và bảng/cột, rồi chạy model/test trong DuckDB.
   Đây là nơi đọc số model chạy được, số test đạt và bảng output.
   Sandbox chạy model/test không tự chứng minh DAG đã chạy trên Airflow.

7. E4 Tối ưu -> V3 Đối chiếu
   Thử viết lại truy vấn, kiểm tra kết quả và thời gian chạy.
   applied = có bản tối ưu được áp dụng.
   skipped = giữ bản gốc; có thể là quyết định đúng nếu ứng viên làm
   lệch kết quả, chậm hơn hoặc không đạt mức cải thiện cần thiết.
   Dấu đỏ V3 có thể chỉ là một ứng viên bị loại; đọc quyết định cuối.

8. Đóng gói -> J2 Duyệt — NGƯỜI DÙNG THAO TÁC
   Người dùng xem code và bằng chứng, duyệt hoặc từ chối kèm ghi chú.
   Có ảnh Hoàn tất hoặc API status=approved mới ghi đã duyệt cuối.

======================================================================
PHẦN 04 — CÁCH TỰ THỰC HIỆN MỘT CA
======================================================================
1) Mở http://localhost:3000 khi Docker đang chạy; kiểm tra chế độ LLM.
2) Sao chép yêu cầu của ca vào ô tạo yêu cầu mới.
3) Trả lời câu hỏi làm rõ nếu có. Ghi lại chính xác lựa chọn của mình.
4) Đọc và duyệt kế hoạch J1b, chụp ảnh kế hoạch.
5) Đợi sinh code/test và sandbox; chụp ảnh tiến trình, output hoặc lỗi.
6) Nếu đi tới bản duyệt, xem code và quyết định tối ưu rồi xử lý J2.
7) Ghi Run ID, ngày giờ, provider, trạng thái cuối và bằng chứng của lần mới.
   Chạy lại sau khi sửa lỗi phải ghi riêng, không xóa bằng chứng lần lỗi.

======================================================================
PHẦN 05 — PHẠM VI KẾT LUẬN
======================================================================
ĐẠT LUỒNG: các bước sản phẩm được thực hiện thành công theo bằng chứng.
KHÔNG ĐẠT: có lỗi thực tế chặn mục tiêu của ca.
CHƯA ĐỦ BẰNG CHỨNG: chỉ thấy một phần luồng, chưa xác nhận kết thúc.

Các ca có output đang ghi số ứng dụng thực sự xuất ra. Muốn khẳng định
từng số liệu nghiệp vụ đúng, cần thêm phép tính hoặc SQL đối chứng độc lập
từ nguồn. Báo cáo không tự coi mọi số tiền là đúng chỉ vì test đạt.

======================================================================
PHẦN 06 — BẰNG CHỨNG ĐƯỢC LƯU Ở ĐÂU?
======================================================================
Thư mục này chứa 5 file TC và file hướng dẫn.
Thư mục evidence/ chứa ảnh có tiền tố TC-01- đến TC-05-.
TC-03 có thêm generated-files.json và error-log.txt.
TC-04 có api-snapshot.json để xác nhận trạng thái đã duyệt và output.
TC-05 có API snapshot, code sinh ra và tên cột sandbox để ghi nhận
trạng thái chờ duyệt và vấn đề ETL nạp nguyên các cột nhạy cảm vào raw.
Thông tin ghi từ API/log được phân biệt với nội dung nhìn thấy trên ảnh.
