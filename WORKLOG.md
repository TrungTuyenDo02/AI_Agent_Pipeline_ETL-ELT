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
| TrungTuyenDo02 | Viết lại README, BAO_CAO, kịch bản video, dàn ý slide; thêm kiểm link `.md` | ✅ Done | 210 file .md, 0 link chết; `pytest` 624 passed, độ phủ 91,76% | — |

---

<!-- Format: copy khối trên cho mỗi ngày làm việc. Status: ✅ Done · 🔄 Doing · ⚠️ Chưa sửa · ⏳ Chưa làm -->
