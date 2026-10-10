# Chi tiết công việc theo ngày

> Nguyên văn các dòng WORKLOG gốc (trước khi rút gọn ngày 2026-10-10), chia theo ngày. Bảng tóm tắt ở [../WORKLOG.md](../WORKLOG.md).
> Không sửa số liệu: đây là bản lưu để truy lại chi tiết.


## 2026-10-02

### 2026-10-02 · việc 1: Dựng khung dự án: cấu hình, Docker, CI, hợp đồng dữ liệu, LLM mock, CL…

- **Người làm:** TrungTuyenDo02
- **Việc:** Dựng khung dự án: cấu hình, Docker, CI, hợp đồng dữ liệu, LLM mock, CLI doctor/seed
- **Trạng thái:** ✅ Done
- **Kết quả:** `python scripts/tasks.py ci` xanh; `doctor` và `seed` chạy được
- **Thời gian:** —

### 2026-10-02 · việc 2: Viết các node kiểm chứng V0/V1/V2, Planner, Codegen và Testgen mù code…

- **Người làm:** TrungTuyenDo02
- **Việc:** Viết các node kiểm chứng V0/V1/V2, Planner, Codegen và Testgen mù code
- **Trạng thái:** ✅ Done
- **Kết quả:** Test chặn DROP/ATTACH/INSTALL/COPY, bắt tên bảng/cột bịa, `dbt build` thật
- **Thời gian:** —

### 2026-10-02 · việc 3: Viết Optimizer và V3, graph đầy đủ J1/J2/cứu hộ, gộp luật viết lại từ …

- **Người làm:** TrungTuyenDo02
- **Việc:** Viết Optimizer và V3, graph đầy đủ J1/J2/cứu hộ, gộp luật viết lại từ nhánh optimizer
- **Trạng thái:** ✅ Done
- **Kết quả:** TPC-H sf=0.1: 11/13 query được áp dụng, nhanh hơn 51%–94,7%
- **Thời gian:** —

### 2026-10-02 · việc 4: Nhập ELT-Bench-Verified (10 pipeline) và đưa tập con ~700 KB vào repo…

- **Người làm:** TrungTuyenDo02
- **Việc:** Nhập ELT-Bench-Verified (10 pipeline) và đưa tập con ~700 KB vào repo
- **Trạng thái:** ✅ Done
- **Kết quả:** Model chuẩn: 3/3 khớp; `pytest` 212 passed, độ phủ 89,87%
- **Thời gian:** —

### 2026-10-02 · việc 5: Build và chạy lại Docker sau khi dọn ổ C:…

- **Người làm:** TrungTuyenDo02
- **Việc:** Build và chạy lại Docker sau khi dọn ổ C:
- **Trạng thái:** ✅ Done
- **Kết quả:** Image 1,45 GB; `/health` ok; luồng mô phỏng tới approved
- **Thời gian:** —

### 2026-10-02 · việc 6: Chạy luồng bằng OpenAI thật, sửa lỗi lộ ra, chọn model theo từng bước…

- **Người làm:** TrungTuyenDo02
- **Việc:** Chạy luồng bằng OpenAI thật, sửa lỗi lộ ra, chọn model theo từng bước
- **Trạng thái:** ✅ Done
- **Kết quả:** gpt-5.6-luna: 5/5 tới bước duyệt, 4/5 không sửa vòng nào, 0,0205 USD/lần
- **Thời gian:** —

### 2026-10-02 · việc 7: Làm bộ golden 12 ca, mutation test, `eval/run_eval.py`; chạy golden và…

- **Người làm:** TrungTuyenDo02
- **Việc:** Làm bộ golden 12 ca, mutation test, `eval/run_eval.py`; chạy golden và ELT-Bench bằng LLM thật
- **Trạng thái:** ✅ Done
- **Kết quả:** Golden 12/12 đúng; mutation 11/12 (91,7%); ELT-Bench 7/34
- **Thời gian:** —

### 2026-10-02 · việc 8: Viết API FastAPI chạy nền, chốt một vai trò DE tự duyệt được…

- **Người làm:** TrungTuyenDo02
- **Việc:** Viết API FastAPI chạy nền, chốt một vai trò DE tự duyệt được
- **Trạng thái:** ✅ Done
- **Kết quả:** `pytest`: 296 passed, độ phủ 90,06%
- **Thời gian:** —

### 2026-10-02 · việc 9: Viết web Next.js, làm giàu kho dữ liệu P113 Retail, thêm bước J1b duyệ…

- **Người làm:** TrungTuyenDo02
- **Việc:** Viết web Next.js, làm giàu kho dữ liệu P113 Retail, thêm bước J1b duyệt kế hoạch
- **Trạng thái:** ✅ Done
- **Kết quả:** Kho 19 bảng, 8 hệ thống, ~58.000 dòng; `pytest` 328 passed (sau kho dữ liệu)
- **Thời gian:** —


## 2026-10-03

### 2026-10-03 · việc 10: Sửa hai lỗi chạy thật trên kho dữ liệu công ty: lỗi nội bộ do mở DuckD…

- **Người làm:** TrungTuyenDo02
- **Việc:** Sửa hai lỗi chạy thật trên kho dữ liệu công ty: lỗi nội bộ do mở DuckDB và Planner hỏi quá nhiều vòng
- **Trạng thái:** ✅ Done
- **Kết quả:** Chạy lại với OpenAI: tới bước chờ duyệt, V2 3/3 test đạt
- **Thời gian:** —

### 2026-10-03 · việc 11: Xử lý góp ý PR: chặn `pre_hook/post_hook` lọt V1, luật viết lại bỏ biể…

- **Người làm:** TrungTuyenDo02
- **Việc:** Xử lý góp ý PR: chặn `pre_hook/post_hook` lọt V1, luật viết lại bỏ biểu thức không tất định
- **Trạng thái:** ✅ Done
- **Kết quả:** `pytest`: 349 passed, độ phủ 91,57%
- **Thời gian:** —


## 2026-10-05

### 2026-10-05 · việc 12: Chuẩn hóa prompt v2, structured output strict, ngữ cảnh gọn, đo token …

- **Người làm:** TrungTuyenDo02
- **Việc:** Chuẩn hóa prompt v2, structured output strict, ngữ cảnh gọn, đo token bằng tiktoken
- **Trạng thái:** ✅ Done
- **Kết quả:** Token đầu vào optimizer 1.483 → 792 (−46,6%); `make ci` 384 passed
- **Thời gian:** —

### 2026-10-05 · việc 13: Ghi nhận hai điểm khi kiểm kê prompt: `references` bị LLM điền sai và …

- **Người làm:** TrungTuyenDo02
- **Việc:** Ghi nhận hai điểm khi kiểm kê prompt: `references` bị LLM điền sai và thiếu `CLAUDE_BASE.md`
- **Trạng thái:** ⚠️ Chưa sửa
- **Kết quả:** Test `relationships` có thể trỏ tới bảng không tồn tại (xem 2026-10-10)
- **Thời gian:** —

### 2026-10-05 · việc 14: Đo các bước V như máy dò: red team V1, đột biến V2, cặp query V3 (0 to…

- **Người làm:** TrungTuyenDo02
- **Việc:** Đo các bước V như máy dò: red team V1, đột biến V2, cặp query V3 (0 token)
- **Trạng thái:** ✅ Done
- **Kết quả:** V1 bắt 58/58, báo nhầm 0/32; `make ci` 477 passed
- **Thời gian:** —

### 2026-10-05 · việc 15: Bổ sung ca khó do Claude viết thay (`ai_proxy`) và sửa V1 theo các ca …

- **Người làm:** TrungTuyenDo02
- **Việc:** Bổ sung ca khó do Claude viết thay (`ai_proxy`) và sửa V1 theo các ca lọt
- **Trạng thái:** ✅ Done
- **Kết quả:** V1 76/78, V2 17/26, V3 19/21, báo nhầm 0; 506 passed
- **Thời gian:** —

### 2026-10-05 · việc 16: Thử LLM thật sớm bằng `eval/smoke_llm.py` trên 3 yêu cầu golden…

- **Người làm:** TrungTuyenDo02
- **Việc:** Thử LLM thật sớm bằng `eval/smoke_llm.py` trên 3 yêu cầu golden
- **Trạng thái:** ✅ Done
- **Kết quả:** 3/3 qua V0 và V1, 0,0132 USD, cache 36,1%
- **Thời gian:** —

### 2026-10-05 · việc 17: Chạy lại golden 12 ca bằng LLM thật, so prompt v1 với v5…

- **Người làm:** TrungTuyenDo02
- **Việc:** Chạy lại golden 12 ca bằng LLM thật, so prompt v1 với v5
- **Trạng thái:** ✅ Done
- **Kết quả:** Đúng 12/12; đạt ngay 11/12 (v1 10/12); chi phí/ca +27,5%
- **Thời gian:** —

### 2026-10-05 · việc 18: Làm giao diện: `tokens.css`, đường ống E/V/J, kiểm tương phản, phông, …

- **Người làm:** TrungTuyenDo02
- **Việc:** Làm giao diện: `tokens.css`, đường ống E/V/J, kiểm tương phản, phông, chế độ sáng/tối
- **Trạng thái:** ✅ Done
- **Kết quả:** Tương phản 34/34 cặp ≥ 4,5:1
- **Thời gian:** —

### 2026-10-05 · việc 19: Dựng khung mốc DE làm tay: `PROTOCOL.md`, `check_de.py`, mục so sánh t…

- **Người làm:** TrungTuyenDo02
- **Việc:** Dựng khung mốc DE làm tay: `PROTOCOL.md`, `check_de.py`, mục so sánh trong report
- **Trạng thái:** ✅ Done
- **Kết quả:** Cột DE làm tay: — (chưa có người làm); 527 passed
- **Thời gian:** —


## 2026-10-07

### 2026-10-07 · việc 20: Sửa bộ chấm ELT-Bench (`gt_compare.py`): thời gian, VARIANT, so số ngu…

- **Người làm:** TrungTuyenDo02
- **Việc:** Sửa bộ chấm ELT-Bench (`gt_compare.py`): thời gian, VARIANT, so số nguyên
- **Trạng thái:** ✅ Done
- **Kết quả:** Tự kiểm 34/34 (trước 28/34); `make ci` 560 passed
- **Thời gian:** ~2 giờ

### 2026-10-07 · việc 21: Lưu đầu ra mỗi lần chạy ELT-Bench và chấm lại đợt 2026-10-02 (0 token)…

- **Người làm:** TrungTuyenDo02
- **Việc:** Lưu đầu ra mỗi lần chạy ELT-Bench và chấm lại đợt 2026-10-02 (0 token)
- **Trạng thái:** ✅ Done
- **Kết quả:** Khớp bảng đúng 7/34 → 11/34 (1 lần chạy)
- **Thời gian:** ~1 giờ


## 2026-10-08

### 2026-10-08 · việc 22: Làm giao diện Studio theo mẫu `ai-agent-studio`: khung kính, tab, chuô…

- **Người làm:** TrungTuyenDo02
- **Việc:** Làm giao diện Studio theo mẫu `ai-agent-studio`: khung kính, tab, chuông, màn lần chạy 2 cột | ✅ Done
- **Trạng thái:** Tương phản 54/54 cặp ≥ 4,5:1
- **Kết quả:** 
- **Thời gian:** —

### 2026-10-08 · việc 23: Hiển thị tiến trình thật khi chờ LLM: sự kiện node bắt đầu, đồng hồ, ư…

- **Người làm:** TrungTuyenDo02
- **Việc:** Hiển thị tiến trình thật khi chờ LLM: sự kiện node bắt đầu, đồng hồ, ước lượng theo trung vị
- **Trạng thái:** ✅ Done
- **Kết quả:** `pytest`: 570 passed, độ phủ 92,28%
- **Thời gian:** —

### 2026-10-08 · việc 24: Làm giao diện kiểu "kính trên trời" và dashboard trang chủ, giảm vẽ lạ…

- **Người làm:** TrungTuyenDo02
- **Việc:** Làm giao diện kiểu "kính trên trời" và dashboard trang chủ, giảm vẽ lại không cần thiết
- **Trạng thái:** ✅ Done
- **Kết quả:** Tương phản 68/68 cặp ≥ 4,5:1
- **Thời gian:** —

### 2026-10-08 · việc 25: Thêm đăng nhập 3 vai trò, PostgreSQL + Alembic, theo dõi thay đổi cấu …

- **Người làm:** TrungTuyenDo02
- **Việc:** Thêm đăng nhập 3 vai trò, PostgreSQL + Alembic, theo dõi thay đổi cấu trúc nguồn (`schema_guard`)
- **Trạng thái:** ✅ Done
- **Kết quả:** Bảng `users`, `sessions`, `audit_log`, `schema_snapshots` (migration 0001–0002)
- **Thời gian:** —

### 2026-10-08 · việc 26: Giảm token đầu ra LLM bằng prompt Planner v6, chạy lại golden 12 ca…

- **Người làm:** TrungTuyenDo02
- **Việc:** Giảm token đầu ra LLM bằng prompt Planner v6, chạy lại golden 12 ca
- **Trạng thái:** ✅ Done
- **Kết quả:** Token đầu ra mỗi lượt Planner 1.155 → 825 (−29%); đúng 12/12
- **Thời gian:** —


## 2026-10-10

### 2026-10-10 · việc 27: Sửa CI: thêm `models/` và `tests/` trống cho template, tạo thư mục khi…

- **Người làm:** TrungTuyenDo02
- **Việc:** Sửa CI: thêm `models/` và `tests/` trống cho template, tạo thư mục khi ghi `sources.yml`
- **Trạng thái:** ✅ Done
- **Kết quả:** Clone sạch: 613 passed, 2 xfailed, độ phủ 91,60%
- **Thời gian:** —

### 2026-10-10 · việc 28: Thêm `.gitattributes` ép LF và xóa `.kilo` khỏi git…

- **Người làm:** TrungTuyenDo02
- **Việc:** Thêm `.gitattributes` ép LF và xóa `.kilo` khỏi git
- **Trạng thái:** ✅ Done
- **Kết quả:** Prettier xanh trên clone Windows; `git ls-files .kilo` rỗng
- **Thời gian:** —

### 2026-10-10 · việc 29: Thêm đo p50/p95 API, bộ nhớ đỉnh DuckDB và kiểm tra `references` ở V0…

- **Người làm:** TrungTuyenDo02
- **Việc:** Thêm đo p50/p95 API, bộ nhớ đỉnh DuckDB và kiểm tra `references` ở V0
- **Trạng thái:** ✅ Done
- **Kết quả:** `/health` p50 3,2 ms; `GET /runs/{id}` p95 15,3 ms (`api_latency.md`)
- **Thời gian:** —

### 2026-10-10 · việc 30: Bớt chật giao diện: gộp bước đã xong, tab ở màn duyệt, chi tiết kỹ thu…

- **Người làm:** TrungTuyenDo02
- **Việc:** Bớt chật giao diện: gộp bước đã xong, tab ở màn duyệt, chi tiết kỹ thuật thu gọn
- **Trạng thái:** ✅ Done
- **Kết quả:** Màn duyệt cao 4.932 → 2.084 px (1440px)
- **Thời gian:** —

### 2026-10-10 · việc 31: Viết `docs/DATABASE.md` sau khi chạy thử migration, sao lưu/khôi phục,…

- **Người làm:** TrungTuyenDo02
- **Việc:** Viết `docs/DATABASE.md` sau khi chạy thử migration, sao lưu/khôi phục, test PostgreSQL
- **Trạng thái:** ✅ Done
- **Kết quả:** Test với PostgreSQL thật: 100 passed
- **Thời gian:** —

### 2026-10-10 · việc 32: Rút gọn WORKLOG, chuyển nguyên văn sang `docs/worklog-detail.md`, thêm…

- **Người làm:** TrungTuyenDo02
- **Việc:** Rút gọn WORKLOG, chuyển nguyên văn sang `docs/worklog-detail.md`, thêm `scripts/check_worklog.py`
- **Trạng thái:** ✅ Done
- **Kết quả:** 39 dòng gốc → bảng 5 ô, kiểm tra tự động trong CI
- **Thời gian:** —

