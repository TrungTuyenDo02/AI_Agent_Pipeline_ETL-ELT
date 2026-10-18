# Worklog — Team P-113

> Ghi lại công việc theo ngày: ai làm gì, kết quả gì. Mỗi dòng một việc; chi tiết nguyên văn ở [docs/worklog-detail.md](docs/worklog-detail.md).

---

## 2026-10-02

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Dựng khung dự án: cấu hình, Docker, CI, hợp đồng dữ liệu, LLM mock, CLI doctor/seed | ✅ Done | `python scripts/tasks.py ci` xanh; `doctor` và `seed` chạy được | — |
| TrungTuyenDo02 | Viết các node kiểm chứng V0/V1/V2, Planner, Codegen và Testgen mù code | ✅ Done | Test chặn DROP/ATTACH/INSTALL/COPY, bắt tên bảng/cột bịa, `dbt build` thật | — |
| TrungTuyenDo02 | Viết Optimizer và V3, graph đầy đủ J1/J2/cứu hộ, gộp luật viết lại từ nhánh optimizer | ✅ Done | TPC-H sf=0.1: 11/13 query được áp dụng, nhanh hơn 51%–94,7% | — |
| TrungTuyenDo02 | Nhập ELT-Bench-Verified (10 pipeline) và đưa tập con ~700 KB vào repo | ✅ Done | Model chuẩn: 3/3 khớp; `pytest` 212 passed, độ phủ 89,87% | — |
| TrungTuyenDo02 | Build và chạy lại Docker sau khi dọn ổ C: | ✅ Done | Image 1,45 GB; `/health` ok; luồng mô phỏng tới approved | — |
| TrungTuyenDo02 | Chạy luồng bằng OpenAI thật, sửa lỗi lộ ra, chọn model theo từng bước | ✅ Done | gpt-5.6-luna: 5/5 tới bước duyệt, 4/5 không sửa vòng nào, 0,0205 USD/lần | — |
| TrungTuyenDo02 | Làm bộ golden 12 ca, mutation test, `eval/run_eval.py`; chạy golden và ELT-Bench bằng LLM thật | ✅ Done | Golden 12/12 đúng; mutation 11/12 (91,7%); ELT-Bench 7/34 | — |
| TrungTuyenDo02 | Viết API FastAPI chạy nền, chốt một vai trò DE tự duyệt được | ✅ Done | `pytest`: 296 passed, độ phủ 90,06% | — |
| TrungTuyenDo02 | Viết web Next.js, làm giàu kho dữ liệu P113 Retail, thêm bước J1b duyệt kế hoạch | ✅ Done | Kho 19 bảng, 8 hệ thống, ~58.000 dòng; `pytest` 328 passed (sau kho dữ liệu) | — |

---

## 2026-10-03

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Sửa hai lỗi chạy thật: mở DuckDB sai cấu hình và Planner hỏi quá nhiều vòng | ✅ Done | Chạy lại với OpenAI: tới bước chờ duyệt, V2 3/3 test đạt | — |
| TrungTuyenDo02 | Xử lý góp ý PR: chặn `pre_hook/post_hook` lọt V1, luật viết lại bỏ biểu thức không tất định | ✅ Done | `pytest`: 349 passed, độ phủ 91,57% | — |

---

## 2026-10-05

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Chuẩn hóa prompt v2, structured output strict, ngữ cảnh gọn, đo token bằng tiktoken | ✅ Done | Token đầu vào optimizer 1.483 → 792 (−46,6%); `make ci` 384 passed | — |
| TrungTuyenDo02 | Ghi nhận hai điểm khi kiểm kê prompt: `references` bị LLM điền sai và thiếu `CLAUDE_BASE.md` | ⚠️ Chưa sửa | Test `relationships` có thể trỏ tới bảng không tồn tại (xem 2026-10-10) | — |
| TrungTuyenDo02 | Đo các bước V như máy dò: red team V1, đột biến V2, cặp query V3 (0 token) | ✅ Done | V1 bắt 58/58, báo nhầm 0/32; `make ci` 477 passed | — |
| TrungTuyenDo02 | Bổ sung ca khó do Claude viết thay (`ai_proxy`) và sửa V1 theo các ca lọt | ✅ Done | V1 76/78, V2 17/26, V3 19/21, báo nhầm 0; 506 passed | — |
| TrungTuyenDo02 | Thử LLM thật sớm bằng `eval/smoke_llm.py` trên 3 yêu cầu golden | ✅ Done | 3/3 qua V0 và V1, 0,0132 USD, cache 36,1% | — |
| TrungTuyenDo02 | Chạy lại golden 12 ca bằng LLM thật, so prompt v1 với v5 | ✅ Done | Đúng 12/12; đạt ngay 11/12 (v1 10/12); chi phí/ca +27,5% | — |
| TrungTuyenDo02 | Làm giao diện: `tokens.css`, đường ống E/V/J, kiểm tương phản, phông, chế độ sáng/tối | ✅ Done | Tương phản 34/34 cặp ≥ 4,5:1 | — |
| TrungTuyenDo02 | Dựng khung mốc DE làm tay: `PROTOCOL.md`, `check_de.py`, mục so sánh trong report | ✅ Done | Cột DE làm tay: — (chưa có người làm); 527 passed | — |

---

## 2026-10-07

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Sửa bộ chấm ELT-Bench (`gt_compare.py`): thời gian, VARIANT, so số nguyên | ✅ Done | Tự kiểm 34/34 (trước 28/34); `make ci` 560 passed | ~2 giờ |
| TrungTuyenDo02 | Lưu đầu ra mỗi lần chạy ELT-Bench và chấm lại đợt 2026-10-02 (0 token) | ✅ Done | Khớp bảng đúng 7/34 → 11/34 (1 lần chạy) | ~1 giờ |

---

## 2026-10-08

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Làm giao diện Studio theo mẫu `ai-agent-studio`: khung kính, tab, chuông, màn lần chạy 2 cột | ✅ Done | Tương phản 54/54 cặp ≥ 4,5:1 | — |
| TrungTuyenDo02 | Hiển thị tiến trình thật khi chờ LLM: sự kiện node bắt đầu, đồng hồ, ước lượng theo trung vị | ✅ Done | `pytest`: 570 passed, độ phủ 92,28% | — |
| TrungTuyenDo02 | Làm giao diện kiểu "kính trên trời" và dashboard trang chủ, giảm vẽ lại không cần thiết | ✅ Done | Tương phản 68/68 cặp ≥ 4,5:1 | — |
| TrungTuyenDo02 | Thêm đăng nhập 3 vai trò, PostgreSQL + Alembic, theo dõi thay đổi cấu trúc nguồn (`schema_guard`) | ✅ Done | Bảng `users`, `sessions`, `audit_log`, `schema_snapshots` (migration 0001–0002) | — |
| TrungTuyenDo02 | Giảm token đầu ra LLM bằng prompt Planner v6, chạy lại golden 12 ca | ✅ Done | Token đầu ra mỗi lượt Planner 1.155 → 825 (−29%); đúng 12/12 | — |

---

## 2026-10-10

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Sửa CI: thêm `models/` và `tests/` trống cho template, tạo thư mục khi ghi `sources.yml` | ✅ Done | Clone sạch: 613 passed, 2 xfailed, độ phủ 91,60% | — |
| TrungTuyenDo02 | Thêm `.gitattributes` ép LF và xóa `.kilo` khỏi git | ✅ Done | Prettier xanh trên clone Windows; `git ls-files .kilo` rỗng | — |
| TrungTuyenDo02 | Thêm đo p50/p95 API, bộ nhớ đỉnh DuckDB và kiểm tra `references` ở V0 | ✅ Done | `/health` p50 2,2 ms; `GET /runs/{id}` p95 15,3 ms (`api_latency.md`) | — |
| TrungTuyenDo02 | Bớt chật giao diện: gộp bước đã xong, tab ở màn duyệt, chi tiết kỹ thuật thu gọn | ✅ Done | Màn duyệt cao 4.932 → 2.084 px (1440px) | — |
| TrungTuyenDo02 | Viết `docs/DATABASE.md` sau khi chạy thử migration, sao lưu/khôi phục, test PostgreSQL | ✅ Done | Test với PostgreSQL thật: 100 passed | — |
| TrungTuyenDo02 | Rút gọn WORKLOG, chuyển nguyên văn sang `docs/worklog-detail.md`, thêm `scripts/check_worklog.py` | ✅ Done | 39 dòng gốc → bảng 5 ô, kiểm tra tự động trong CI | — |
| TrungTuyenDo02 | Viết API.md, CONFIG.md, hai hướng dẫn deploy, proxy `rewrites` cho đăng nhập cùng miền | ✅ Done | Đăng nhập qua proxy đã thử trên máy; lệnh cloud ghi chưa chạy thật | — |
| TrungTuyenDo02 | Viết lại README, BAO_CAO, kịch bản video, dàn ý slide; thêm kiểm link `.md` | ✅ Done | 210 file .md, 0 link chết; `pytest` 626 passed, độ phủ 91,76% | — |

## 2026-10-12

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Chặn dữ liệu chứa `</data>` thoát khỏi khối dữ liệu của prompt (prompt injection), test cả 4 prompt | ✅ Done | `llm.neutralize_data_tags`; `test_prompt_injection.py` 21 ca đạt | — |
| TrungTuyenDo02 | Thêm quét từ khóa injection/bí mật, chỉ cảnh báo ở hồ sơ dữ liệu và sổ lỗi | ✅ Done | `src/agents/tools/injection_scan.py`; 20 ca test | — |
| TrungTuyenDo02 | Thêm câu chống injection vào 4 prompt, lọc mật khẩu/DATABASE_URL khỏi môi trường dbt, thêm ca TRUNCATE | ✅ Done | +24–26 token tĩnh mỗi prompt, vẫn trong ngân sách; `pytest` 671 passed, độ phủ 91,81% | — |
| TrungTuyenDo02 | Đo hiệu quả câu dặn chống injection với LLM thật | ⏳ Chưa làm | Cần khóa API và bộ eval injection | — |


## 2026-10-13

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Neon nhánh `dev`: chạy `alembic upgrade head`, thêm `connect_timeout=15` | ✅ Done | Bản `0002_schema_snapshots`; `p113_app` chỉ có quyền tối thiểu; 42 test đăng nhập đạt trên Neon `p113_test` | — |
| TrungTuyenDo02 | Chọn dd/mm hay mm/dd theo bằng chứng; chưa chắc thì báo ở Dữ liệu nguồn và màn duyệt | ✅ Done | 4 ca test (VN, Mỹ, lẫn, mơ hồ) | — |
| TrungTuyenDo02 | CLAUDE.md 2.3: LLM chỉ thấy cấu trúc và con số; code điền giá trị cột cho người tick | ✅ Done | Planner v8 (tĩnh +79, động −213 token/3 nguồn); `pytest` 696 passed; độ phủ 91,92% | — |
| TrungTuyenDo02 | Đổi sang gpt-6-luna (`temperature: false`), đo Planner v8 bằng LLM thật (`smoke-llm`) | ✅ Done | 3/3 qua V0/V1, 0 câu hỏi thừa, 0,00577 USD (trước 0,00997); g06 lỗi cú pháp 1/4 lần | — |
| TrungTuyenDo02 | Tạo `.env.production.example`; thử pooler Neon với prepared statement | ✅ Done | 60/60 lượt, 3 luồng, 0 lỗi; bản Render là demo (SQLite mất khi khởi động lại) | — |
| TrungTuyenDo02 | Mục 14: lần chạy kẹt, tối đa 2 lần chạy/người, vị trí hàng đợi, trần 1 USD/người/ngày | ✅ Done | Vượt giới hạn trả 429; `doctor` báo model thiếu giá; 6 test mới | — |
| TrungTuyenDo02 | Đổi icon sang Phosphor, bỏ ký tự ✓ ✗ ⚠ làm icon | ✅ Done | `lib/icons.ts`; build + chụp 8 màn (sáng/tối) bằng Chrome headless | — |

## 2026-10-14

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Giao diện mục 9 bước 1–2: bảng màu kiểu Apple, kính mờ cho thanh trên và menu | ✅ Done | Mọi cặp chữ/nền ≥ 4.5:1 (sáng + tối); không còn mã màu cứng | — |
| TrungTuyenDo02 | Bước 3: đăng nhập gradient lưới + thẻ kính; thẻ thống kê màu, số nhảy, bấm để lọc | ✅ Done | Thử form thật: sai mật khẩu báo chung, đúng vào trang chủ; `/runs?loc=…` lọc khớp số | — |
| TrungTuyenDo02 | Bước 4: thanh trượt điều hướng, Ctrl/Cmd + K, MotionConfig giảm chuyển động | ✅ Done | Thử bằng phím thật trên Chrome headless; `make frontend-check` đạt | — |
| TrungTuyenDo02 | Bước 5: toast, khung xám khi tải, trạng thái rỗng có icon, hộp xác nhận khi Duyệt (Radix) | ✅ Done | Thử thật: Esc hủy không gửi, xác nhận thì ghi duyệt và hiện toast | — |
| TrungTuyenDo02 | Bước 6: dock trái, thanh dưới đáy điện thoại, bảng Lần chạy xếp dọc trên điện thoại | ✅ Done | Chụp 1440/820/390px; không tràn ngang; sửa bảng Cài đặt lộ chữ phía sau | — |
| TrungTuyenDo02 | Bước 7: dòng thời gian vòng 28px, icon xoay khi chạy, dấu tích tự vẽ khi xong | ✅ Done | Đo góc xoay thay đổi; lint, kiểu, định dạng, tương phản, build đều đạt | — |
| TrungTuyenDo02 | CLAUDE.md bản 2, giai đoạn 1: cửa kiểm tra đầu vào tầng 0–1 và trần chi phí | ✅ Done | Chặn nhầm 0/10 câu hợp lệ; lọt vô nghĩa/tấn công 0/20; 44 test mới; không gọi LLM | — |
| TrungTuyenDo02 | Giai đoạn 2: cửa kiểm tra tầng 2 (model nhỏ), hỏi bổ sung bằng mẫu cố định, màn nhập web | ✅ Done | ~400 token vào, ≈ 1,2% chi phí một lần chạy (ước tính); mock 0/50 sai; 61 test cổng; chưa đo LLM thật | — |
| TrungTuyenDo02 | Giai đoạn 3: sổ nguồn, phân quyền phòng ban, build_llm_context, scrub_error, tách người duyệt | ✅ Done | Migration 0005; 3 mức truy cập; kiểm rò rỉ 0 giá trị thật; đo độ đúng LLM thật chưa làm | — |
| TrungTuyenDo02 | Giai đoạn 4: khung Extract, 3 bộ nạp (tệp, DuckDB, PostgreSQL chỉ đọc), lựa chọn pipeline ở J1b | ✅ Done | 128 test mới; PostgreSQL thật qua Neon (RUN_PG_TESTS=1) đạt; luồng qua DuckDB/PG khớp luồng tệp; golden 11/11, mutation 11/12 giữ nguyên | — |
| TrungTuyenDo02 | Giai đoạn 5: phát hiện thay đổi cấu trúc nguồn, pipeline tự phòng thủ, mô phỏng 6 kịch bản | ✅ Done | 6 kịch bản: 4 chặn/fail sớm, 1 vô hại, 1 cảnh báo; 0 sai âm thầm; mutation 14/15; chỉ mock | — |
| TrungTuyenDo02 | Giai đoạn 6: từ điển nghiệp vụ, Planner nhận thuật ngữ, 5 ca golden mới | ✅ Done | Thuật ngữ cần thiết 6/6; token Planner +13,5%; độ đúng chưa đo LLM thật | — |
| TrungTuyenDo02 | Giao diện thay đổi cấu trúc: nút đỏ ở chuông, so sánh trước/sau, đề xuất sửa pipeline | ✅ Done | Thêm ca type_narrowed, nullable_tightened; Gemini chỉ diễn giải khi bấm; mock only | — |
| TrungTuyenDo02 | Chạy eval phần kiểm bằng code, cập nhật report và README | ✅ Done | 1114 test đạt; độ phủ 91,82%; golden 16/16; mutation 14/15; không gọi LLM thật | — |
| TrungTuyenDo02 | Số đỏ trên tab điều hướng; script demo/seed_drift.py tạo thay đổi giả để xem giao diện | ✅ Done | Hook useDriftAlerts dùng chung cho chuông, tab và trang; số đỏ giảm ngay sau khi xác nhận (sự kiện drift:refresh) | — |
| TrungTuyenDo02 | Bản vá nhanh schema drift (ADR 0012), tái dùng đặc tả và sửa SQL tất định | ✅ Done | 5/6 kịch bản vá 0 token, đầu ra khớp; ca cần AI dùng 8.327 token; Gemini diễn giải đã chạy thật | — |
| TrungTuyenDo02 | Tinh gọn trang đăng nhập, thêm luồng màu, công cụ và 4 số đo | ✅ Done | Bỏ khung lệnh và dữ liệu mẫu; giải thích dài vào tooltip; tương phản đạt | — |
| TrungTuyenDo02 | Sửa xác thực trong hướng dẫn, đối chiếu bản vá và đồng bộ tài liệu | ✅ Done | CI: 1124 đạt, phủ 91.83%; frontend kiểm tra đạt; thêm 9 test hồi quy | — |
| TrungTuyenDo02 | Thêm dataset và bộ chấm Extract độc lập, lọc nguồn trước khi đọc nội dung | ✅ Done | Eval 21/21; CI 1149 đạt, phủ 91.85%; chặn đọc ngoài quyền; 0 LLM | — |

## 2026-10-17

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Sổ chi phí LLM, giữ trước ngân sách mỗi lượt gọi, chặn model thiếu giá (ADR 0014) | ✅ Done | CI 1183 đạt, phủ 92.02%; 20 test mới, tranh chấp SQLite và PostgreSQL không vượt trần; 0 token | — |
| TrungTuyenDo02 | Nâng Neon lên head; migration 0009 cấp quyền glossary_terms mà 0007 bỏ sót | ✅ Done | Neon ở 0009, p113_app đủ quyền; demo trên Neon đạt; test quét GRANT mọi bảng | — |
| TrungTuyenDo02 | Giả lập deploy Vercel trên máy: build có BACKEND_URL, gọi API qua rewrite | ✅ Done | Đăng nhập, cookie HttpOnly, lần chạy mock tới approved, tải zip 200; chưa deploy Vercel thật | — |
| TrungTuyenDo02 | Xử lý review PR #8: scrub_error che giá trị không nháy, chụp cấu trúc chịu tranh chấp, cột tên lạ | ✅ Done | 13 test mới tái hiện lỗi trước khi sửa; 2 điểm bot báo nhầm (SQL injection, ReDoS) đã kiểm và ghi lý do | — |
| TrungTuyenDo02 | Chế độ khách bằng dữ liệu mẫu, chỉ ở frontend (`/demo`, ADR 0015) | ✅ Done | Headless: luồng Engineer → Reviewer trọn vẹn, 0 request tới backend; đăng nhập thường không đổi; CI 1205 đạt | — |

---

## 2026-10-18

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| TrungTuyenDo02 | Hướng dẫn nhúng sẵn trong chế độ khách: quy trình 4 bước, giải thích từng giai đoạn, từ điển | ✅ Done | Headless: 4 bước đổi đúng 8 giai đoạn, lần chạy dừng báo đúng bước; người dùng thường không thấy hướng dẫn | — |
| TrungTuyenDo02 | Trang `/docs` công khai, tiến độ đọc từ `lib/projectStatus.ts`, liên kết Tài liệu | ✅ Done | Mở được khi chưa đăng nhập; ý dài nhất 54 từ; đổi 2 mục → thanh 1/10 đúng; CI 1205 đạt | — |
| TrungTuyenDo02 | Hoàn thiện tạm dừng/tiếp tục lần chạy (ADR 0016): sửa 2 test sai giả định, lỗi tham số PostgreSQL | ✅ Done | Pause API 17/17 trên SQLite; PostgreSQL 16 tạm 63/63; nút chỉ hiện cho người tạo; CI 1211 đạt | — |
| TrungTuyenDo02 | Sửa lỗi review: run vá mất đầu vào khi tạm dừng xếp hàng; tiếp tục đồng thời vượt hạn mức | ✅ Done | 3 test tái hiện lỗi trước khi sửa; đầu vào bản vá lưu lúc tạo; kiểm hạn mức trong khóa hàng đợi; CI 1214 đạt | — |
| TrungTuyen | Hiển thị PipeSmith và linh vật Pip theo trạng thái lần chạy | ✅ Done | Frontend-check đạt; sáu tư thế; Galey SemiBold tải thật, kiểm laptop và điện thoại không tràn ngang | — |
| TrungTuyen | Pip bám mép: kéo đổi góc, lưu vị trí, bong bóng và đường đi ngắn | ✅ Done | Frontend-check đạt; 26 kiểm tra Chromium đạt trên desktop, điện thoại và chế độ giảm chuyển động | — |
| TrungTuyen | Hiện Pip ngay trên Trang chủ và danh sách, gồm chế độ khách | ✅ Done | Frontend-check đạt; 12 kiểm tra Chromium đạt; không trùng linh vật khi chuyển trang, ẩn/hiện giữ xuyên trang | — |
| TrungTuyen | Đổi bong bóng Pip chế độ sáng sang xanh ngọc nhạt | ✅ Done | Build, định dạng và tương phản đạt (thấp nhất 4,76:1); kiểm sáng/tối, laptop và điện thoại đạt | — |
| TrungTuyen | Landing `/docs`: nhịp màu theo khối, màu nhấn phụ, khối Cách hoạt động, chữ gom vào `content/landing.ts` | ✅ Done | Tương phản AA mọi cặp; build đạt; chụp 1440px, 375px, sáng/tối không tràn; mỗi đoạn tối đa 2 dòng | — |
| TrungTuyen | Trang đăng nhập: sửa chồng lớp, ba điểm nổi bật, demo động kèm bảng kết quả, số liệu phần trăm | ✅ Done | Số từ README (93%, 86%, 6/6, 92%, 7×); bảng là 3/30 dòng thật fct_daily_revenue của lần chạy mẫu; màn hẹp form lên trước | — |
| TrungTuyen | Kiểm chữ giao diện: `npm run lint:text` tự viết, sửa viết hoa đầu nhãn, thêm vào CI | ✅ Done | Sửa 19 chuỗi, ghi `docs/spellcheck-report.md`; lint:text sạch; thuật ngữ thống nhất "duyệt" | — |

---

<!-- Format: copy khối trên cho mỗi ngày làm việc. Status: ✅ Done · 🔄 Doing · ⚠️ Chưa sửa · ⏳ Chưa làm -->
