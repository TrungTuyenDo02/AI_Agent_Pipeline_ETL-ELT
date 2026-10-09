# Weekly Journal — Team P-113

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.

---

## Tuần 2026-09-28 → 2026-10-04

### Mục tiêu tuần này
- [x] MVP giai đoạn A: luồng NL → dbt + DAG → sandbox → tối ưu → duyệt, chạy trong terminal không cần khóa
- [ ] Thống nhất cách gộp các nhánh của thành viên vào `main`
- [ ] Bộ eval golden (Phase 6)

### Đã hoàn thành
- Graph LangGraph 17 node khớp sơ đồ J-E-V; tạm dừng J1/J2/cứu hộ bằng interrupt + checkpointer SQLite.
- V-node bằng code: V0 soát spec, V1 sqlglot (chặn lệnh nguy hiểm, tên bịa), V2 dbt build trong DuckDB
  (`enable_external_access=false`, timeout, giới hạn bộ nhớ), V3 đối chiếu hai chiều trên 5 bộ dữ liệu.
- CLI (`doctor`, `seed`, `run`, `answer`, `status`, `review`, `errors`, `optimize`), `demo`; 174 test, độ phủ 89%.

### Quyết định quan trọng
| Quyết định | Lý do | Ghi lại ở |
|---|---|---|
| Tạm dừng bằng `interrupt()` + `SqliteSaver` | Một graph duy nhất, CLI và API dùng chung, `review` chạy ở tiến trình khác vẫn tiếp tục được | `docs/adr/0001-...` |
| CLI dùng argparse, LLM `mock` mặc định | Không thêm dependency; chạy không cần khóa | `docs/adr/0002-...` |
| V-node bằng code, Testgen mù code | Không dùng LLM chấm LLM; test đối soát độc lập bắt được lỗi SUM→AVG | `docs/adr/0003-...` |
| Tầng raw giữ CSV dạng chuỗi (`all_varchar`) | Tránh DuckDB đoán sai "950.000" là số thực 950.0; ép kiểu ở staging | `src/agents/tools/duckdb_tools.py` |
| Staging `ephemeral`, mart `table`; optimizer tối ưu model đích trên bảng staging đã dựng trong từng bộ dữ liệu | Đối chiếu/benchmark chạy thẳng bằng DuckDB, ghi ngược bản tối ưu về `{{ ref() }}` | `src/agents/nodes/optimizer.py` |
| E4 thử luật tất định → sqlglot → LLM (gộp từ nhánh optimizer) | Rẻ (0 token) và có giả định kiểm chứng được; TPC-H: 10/11 ca áp dụng không cần LLM | `src/agents/tools/rewrite_rules.py` |
| ELT-Bench: chỉ lấy nguồn thô + yêu cầu + bảng đúng, 10 pipeline nhẹ nhất; giữ kiểu dữ liệu như Airbyte nạp | Hệ thống bắt đầu từ dữ liệu đã có trong DuckDB; bảng đúng được tính trên dữ liệu Airbyte nạp nên phải giữ kiểu tương ứng; kiểm chứng bộ chấm bằng model chuẩn trước (3/3 khớp) | `eval/benchmarks/eltbench/` |
| Đưa tập con ELT-Bench (~700 KB) vào repo tại `eval/datasets/eltbench/` | Nhỏ, giấy phép CC BY-SA 4.0 cho phép chia sẻ lại khi ghi nguồn; CI và BTC chạy lại được eval mà không cần tải 4,5 GB | `eval/datasets/eltbench/README.md` |
| Test đối soát: LLM chỉ viết câu tính kết quả kỳ vọng từ raw; phép so sánh hai chiều theo grain (có sai số) do code dựng | gpt-4o-mini viết phép so sánh sai (luôn fail / sai cú pháp); phần so sánh là việc của code theo luật J-E-V. Vẫn mù code của Coder | `src/agents/nodes/testgen.py` |
| V1 biên dịch thử mọi model + test bằng DuckDB `EXPLAIN` (chỉ đọc, nhúng ref như dbt) | Staging là ephemeral nên dbt báo lỗi ở mart, Coder sửa nhầm chỗ; EXPLAIN gắn lỗi đúng file, 0 token | `src/agents/nodes/safety.py` |
| Testgen giữ nguyên test đối soát khi đặc tả không đổi | "Đáp án" không được đổi theo code; tránh tốn token và sinh lỗi mới mỗi vòng | `src/agents/nodes/testgen.py` |
| Model theo từng bước: gpt-5.6-luna (planner/codegen/testgen), gpt-5.6-terra (optimizer); dự phòng Gemini 3.1 Flash-Lite khi OpenAI gọi lỗi | Người dùng chọn hướng C sau khi so giá chính thức (2026-10-02). Dự phòng chỉ khi gọi lỗi, không khi trả sai định dạng. Lưu ý: Codegen và Testgen cùng model → đổi riêng `MODEL_TESTGEN` nếu muốn "khác bộ óc" | `src/config.py`, `src/services/llm.py` |
| Một vai trò DE, tự duyệt được; công tắc `REQUIRE_SEPARATE_REVIEWER` để bật lại luật 2 người | Người dùng chính là DE; bước duyệt vẫn giữ (xem diff + bằng chứng). Đề bài nêu 2 vai trò nên giữ công tắc để demo khi cần | `docs/adr/0004-mot-vai-tro-de.md` |
| (2026-10-08, thay dòng trên) Đăng nhập tài khoản nội bộ (argon2id, phiên phía máy chủ) + 3 vai trò engineer/reviewer/admin; chỉ Reviewer duyệt, được tự duyệt; bỏ công tắc | Người dùng chọn theo CLAUDE.md mục 2–3 (SSO để sau); PostgreSQL trước cho users/sessions/audit_log | `src/services/auth.py`, `src/api/deps.py`, `migrations/` |
| (2026-10-08) Một công ty, một bản triển khai riêng (không multi-tenant); PostgreSQL đặt tại Việt Nam, cùng mạng với backend và thư mục `data/` (dev: docker compose cổng 5433; thật: máy chủ của công ty hoặc PostgreSQL managed của nhà cung cấp cloud có trung tâm dữ liệu ở Việt Nam) | Người dùng chọn. Bảng `users`/`audit_log` chứa tên tài khoản, IP, giờ đăng nhập của nhân viên = dữ liệu cá nhân (Luật BVDLCN 91/2025, NĐ 356/2025; NĐ 53/2022 Đ.26) → lưu trong nước để không phát sinh chuyển dữ liệu ra nước ngoài | `docker-compose.yml`, `.env.example` |
| (2026-10-08) Cấu trúc bảng nguồn thay đổi → cảnh báo KÈM đề xuất bản sửa (qua màn duyệt diff, Reviewer quyết); điểm kiểm tra là lúc đọc file trong `data/sources` | Người dùng chọn (CLAUDE.md mục 8). Xóa cột / nghi đổi tên → dừng, **Engineer** xác nhận từng cặp đổi tên (không tự đoán) rồi chạy tiếp; Reviewer xem lại ở J2; ảnh chụp chỉ thành bản chuẩn khi Reviewer duyệt (bảng `schema_snapshots`, chỉ ghi thêm, khóa theo tên + đường dẫn nguồn) | `src/services/schema_watch.py`, `src/agents/nodes/schema_guard.py` |
| (2026-10-08) GIỮ gửi LLM vài dòng mẫu + 3 giá trị ví dụ đã che PII (lệch CLAUDE.md mục 7, người dùng chọn) | Chất lượng sinh code với dữ liệu lộn xộn. Bù cho mục 9: danh sách giá trị cột phân loại KHÔNG gửi LLM; prompt Codegen v3 cấm lọc theo giá trị chỉ thấy trong mẫu; code tìm mọi điều kiện cứng theo giá trị và tô sáng ở màn duyệt (đánh dấu giá trị không có trong đặc tả); đối chiếu số dòng raw → staging; bộ dữ liệu `dirty` cố ý làm bẩn cột phân loại | `src/agents/tools/sql_tools.py`, `src/agents/nodes/package.py` |
| API chạy graph nền, xếp hàng một luồng; web hỏi tiến trình định kỳ (polling) | Graph chạy tới vài phút; checkpointer SQLite dùng chung một kết nối → không chạy song song; đủ cho demo một DE, đơn giản hơn WebSocket | `src/services/jobs.py` |
| Cấu trúc dữ liệu (schema, lineage, khóa nối) suy ra bằng code, không LLM | DE cần sự thật về dữ liệu; DuckDB DESCRIBE cho kiểu cột, sqlglot cho lineage/JOIN — 0 token, không bịa | `src/services/catalog.py` |
| Web thiết kế cho laptop trước (người dùng chọn), màn nhỏ vẫn dùng được | DE làm việc trên laptop: cần chỗ cho diff code 2 cột và sơ đồ bảng; vẫn giữ responsive vì BTC chấm UI/UX | `frontend/app/globals.css` |
| Sơ đồ dữ liệu tự vẽ bằng SVG (3 cột raw → staging → mart), không thêm thư viện đồ thị | Bố cục theo tầng là đủ và tất định; bớt một dependency lớn | `frontend/lib/diagram.ts` |
| Duyệt xong → DE tải gói `.zip` (dbt + test + DAG) để tự mở PR; agent không tự push | Giữ ràng buộc "con người merge"; không cần quyền GitHub | `src/services/export.py`, `GET /runs/{id}/download` |
| Docker dùng volume riêng thay cho thư mục `data/` gắn từ Windows | Checkpoint SQLite chế độ WAL mất dữ liệu khi gắn thư mục Windows; tạo lại container làm mất trạng thái lần chạy | `docker-compose.yml` |
| Kho raw công ty giả lập "P113 Retail" (8 hệ thống, 19 bảng) do code sinh, không tải bộ công khai | Bộ công khai cần đăng nhập/quá lớn và không biết trước chỗ bẩn; dữ liệu sinh có seed cố định + danh sách bẩn gài sẵn làm đáp án kiểm tra agent | `src/services/company/`, `docs/data-catalog.md` |
| Không đưa mô tả "bảng bẩn ở đâu" vào prompt Planner | Đó là đáp án; agent phải tự phát hiện qua bước soi P | `src/services/company/__init__.py` (systems.yml chỉ cho màn web) |
| Gợi ý khóa nối kèm % dòng khớp đo thật; bỏ cặp khớp < 20% | Trùng tên cột chưa chắc cùng nghĩa (mã đơn Shopee ≠ mã đơn website); % khớp cho DE thấy ngay khóa mồ côi | `src/services/source_catalog.py` |
| Thêm bước J1b: DE duyệt kế hoạch có giải thích (từng bước: làm gì + vì sao) trước khi sinh code | Kế hoạch sai bị chặn trước khi tốn token sinh code/test/sandbox; DE (và người không rành kỹ thuật) hiểu agent định làm gì | `src/agents/nodes/plan_review.py`, ADR 0005 |
| (2026-10-08) Màn "Hồ sơ dữ liệu" kiểu Power Query / Tableau Prep (BA quen dùng): thanh chất lượng hợp lệ/lỗi/rỗng, phân bố từng cột, kết luận nhanh, vấn đề theo luật code, 50 dòng xem trước đã che PII; chạy được trên staging/mart do code AI sinh và trên bộ dữ liệu bẩn | DE nhìn một lần biết dữ liệu ổn chưa; số đo bằng DuckDB, 0 token, không lưu, không gửi LLM. Chỉ Engineer/Reviewer xem (Admin 403). Bộ che PII nay che cả số điện thoại có dấu ngăn (0320.958027) | `src/services/catalog.py`, `frontend/components/catalog/DataProfile.tsx` |
| LangSmith tự tắt khi khóa còn là giá trị mẫu | `.env` copy từ template gây lỗi 403 và làm ồn terminal | `src/services/tracing.py` |

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| sqlglot không báo lỗi khi bảng không tồn tại | Tự kiểm tra tên bảng với danh mục thật trước khi `qualify` | Test `test_unknown_table_is_reported` |
| Model đích lỗi làm sqlglot crash (`SchemaError` bảng rỗng cột) | Không thêm model lỗi vào danh mục; bắt `SchemaError` | Test cứu hộ chạy đúng |
| Terminal Windows cp1252 làm hỏng tiếng Việt | CLI/log/tasks tự chuyển stdout/stderr sang UTF-8 | Demo in đúng tiếng Việt |
| sqlglot.optimizer bỏ mất `CAST(... AS BIGINT)` làm cột đổi kiểu sang HUGEINT | V3 so cả kiểu cột nên loại ứng viên, E4 chuyển sang ứng viên kế | Pipeline mẫu vẫn được tối ưu đúng (+25,7%) |
| Ổ C: đầy 100% làm Docker lỗi I/O, test để lại thư mục tạm | Dọn thư mục tạm của test, `conftest.py` tự dọn; chạy test với TEMP trên ổ F: | Docker cần người dùng giải phóng ổ C: |
| Optimizer báo "nhanh hơn -47%" khi LLM trả lại nguyên câu gốc | So sánh sau chuẩn hóa: giống bản gốc → `skipped` không đo | Test `test_identical_proposal_is_skipped_without_benchmark` |
| Tạo lại container làm mất đặc tả/code của lần chạy (danh sách vẫn còn) | Nguyên nhân: SQLite WAL trên thư mục Windows gắn vào container + `workspaces/` không được gắn. Chuyển sang volume Docker; API tự sinh dữ liệu mẫu khi thư mục nguồn trống | Lần chạy còn nguyên sau `docker compose up` lại |
| docker compose đọc `LLM_PROVIDER=openai` từ `.env` nên bản Docker gọi LLM thật (tốn phí) mà không để ý | Ghi rõ trong RUNBOOK cách ép mock; web hiển thị nhãn "LLM thật"/"Chế độ mô phỏng" ở thanh trên | Người dùng thấy ngay chế độ đang chạy |
| Dữ liệu nhiều bảng làm lộ 5 lỗi có sẵn: E0 nạp SQLite từng dòng (311 giây cho 19 bảng); P không nhận ngày `dd/mm/yyyy hh:mm:ss` nên Coder/Tester đọc ra NULL ~95% dòng POS; mẫu "số thường" khớp nhầm `125.000`; bộ large của E2 nhân bản bảng danh mục mà giữ nguyên khóa ngoại → phép nối bùng nổ (>50 phút CPU); `with sqlite3.connect` không đóng file | E0 đổ SQLite ra JSON tạm rồi DuckDB đọc một lần (3,8 giây); P nhận 7 định dạng ngày + 5 kiểu tiền, đo số giá trị không đọc được, phát hiện biến thể hoa/thường; E2 đổi mọi cột khóa theo bản sao; đóng kết nối SQLite tường minh | Yêu cầu POS thật: lần 1–2 dừng ở cứu hộ, lần cuối qua V2 ngay lần đầu, 240 dòng đúng |

### Bài học
- Model suy luận (gpt-5.x) tính cả token suy luận ẩn vào giới hạn đầu ra: giới hạn 4.000 làm câu trả lời rỗng ở bài khó.
- Test tất định cũng có thể sai giả định (not_null mọi cột): benchmark công khai giúp lộ các giả định này.
- Prompt phải cấm câu hỏi giả định; nếu không, model mạnh hơn lại hỏi đào sâu mãi.
- Kiểm tra các nhánh remote (`git branch -a`) trước khi bắt đầu, không chỉ nhánh hiện tại.
- Số đo tốc độ trên dữ liệu giả lập dao động giữa các lần chạy (21–45%); báo cáo cần ghi rõ điều kiện đo.
- Mock chỉ chứng minh luồng chạy, không chứng minh chất lượng: lần đầu dùng LLM thật, luồng thất bại 100% vì 8 lỗi
  thiết kế mà mock không lộ ra. Sau khi sửa: 4/5 lần đạt. Cần chạy LLM thật sớm, không đợi tới cuối.
- Thông báo lỗi gửi cho LLM phải chỉ đúng file, đúng dòng và nói rõ "đọc được cột nào"; lỗi mơ hồ khiến LLM sửa lung tung.
- Ổ đĩa ảo của Docker Desktop nằm trên C: và không tự co lại: build lớn có thể làm đầy C:.
- Dữ liệu demo 3 bảng nhỏ che giấu lỗi hiệu năng và định dạng; kho nhiều bảng, nhiều kiểu bẩn lộ ngay 5 lỗi của các
  bước kiểm chứng bằng code. Test đối soát "mù code" bắt được Coder và Tester bất đồng, nhưng nếu cả hai cùng đọc sai
  (NULL hàng loạt) thì phải nhờ số đo của bước soi P (`parse_failures`).

### Kế hoạch tuần sau
- [x] Gộp phần phù hợp của `feature/optimizer-agent`; không dùng `feature/sandbox_execution` (đội đã thống nhất)
- [x] Phase 6: bộ golden 12 ca, mutation test, `eval/run_eval.py` (đã chạy bằng LLM thật)
- [x] Có khóa LLM thật (OpenAI + Google dự phòng)
- [x] Giai đoạn B: API (Phase 7) + web (Phase 8)
- [x] Docker chạy lại (backend + frontend)
