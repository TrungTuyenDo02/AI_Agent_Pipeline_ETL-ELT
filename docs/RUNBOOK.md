# RUNBOOK — Hướng dẫn chạy P-113

> Viết cho người không rành code. Làm lần lượt từ trên xuống. Lệnh dưới đây chạy trong **PowerShell** ở thư mục repo.
> Máy có `make` (Linux/macOS/Git Bash) thì có thể dùng `make <đích>` thay cho `python scripts/tasks.py <đích>`.

## 1. Cài môi trường (một lần)

```powershell
python --version                     # cần 3.11.x
python -m venv .venv
.\.venv\Scripts\Activate.ps1         # mỗi lần mở terminal mới đều chạy dòng này
pip install -r requirements.txt
Copy-Item .env.example .env          # nếu đã có .env thì bỏ qua
python -m src.cli doctor
```

`doctor` in danh sách ✓ / ! / ✗:
- ✗ = phải sửa trước khi chạy.
- ! hoặc i = chưa bắt buộc ở giai đoạn hiện tại.

**Giai đoạn A không cần khóa API nào.** Mặc định `LLM_PROVIDER=mock`: câu trả lời của LLM là cố định (mô phỏng),
đủ để chạy và kiểm thử toàn bộ luồng. Màn hình luôn hiện nhãn **"Chế độ mô phỏng"** để không nhầm với mô hình thật.

Nếu `doctor` báo "LangSmith bật nhưng khóa chưa thật": mở `.env`, sửa thành `LANGCHAIN_TRACING_V2=false`.

## 2. Chạy trong terminal

### 2.1 Tạo dữ liệu giả lập

```powershell
python -m src.cli seed                    # kho raw công ty giả lập "P113 Retail": 8 hệ thống, 19 bảng (~58.000 dòng)
python -m src.cli seed --dirty 0.2        # bẩn hơn (mặc định 0.05); --dirty 0 = bản sạch
python -m src.cli seed --scale 2          # gấp đôi số dòng
python -m src.cli seed --profile basic    # chỉ 3 nguồn đơn online (Shopee CSV, Tiki JSON, website SQLite)
```

Dữ liệu nằm trong `data/sources/` (không commit lên git). Danh sách hệ thống, bảng, quan hệ và **các kiểu bẩn đã
gài** (đáp án để kiểm tra agent) ở [docs/data-catalog.md](data-catalog.md). Planner thấy cả 19 bảng và tự chọn bảng
cần dùng; E0 chỉ nạp các bảng được chọn.

### 2.2 DE tạo yêu cầu

```powershell
python -m src.cli run --request "Gộp dữ liệu đơn hàng 3 nguồn, tính doanh thu ngày"
```

Agent chạy từng bước và in ✓/✗, thời gian, token. Khi gặp điểm chưa rõ, agent **hỏi bằng câu trắc nghiệm** (J1):

```
Đơn ở trạng thái nào được tính vào doanh thu?
  1. Chỉ đơn đã giao/hoàn tất
  2. Mọi đơn trừ đơn đã hủy (kể cả đơn hoàn tiền)
Chọn số [1/2]:
```

Gõ số rồi Enter. Agent lập lại kế hoạch và **in kế hoạch có giải thích** (J1b): bảng các bước "Làm gì | Vì sao",
bảng đích, mức gộp. Gõ `approve` để đồng ý, hoặc `revise` rồi nhập cần sửa gì (agent lập lại kế hoạch).

Sau khi đồng ý, agent tự: nạp nguồn → soi dữ liệu → sinh dữ liệu thử → sinh code dbt + DAG Airflow →
sinh test → kiểm tra an toàn → chạy thử trong sandbox → tối ưu query → đối chiếu kết quả. Cuối cùng in:

```
Trạng thái: chờ Reviewer duyệt (run_id: 8ff0c55055)
Xem bằng chứng và duyệt: python -m src.cli review 8ff0c55055
```

#### Cửa kiểm tra đầu vào (G0)

Yêu cầu qua cửa trước khi tạo lần chạy: luật cố định (rỗng, quá ngắn/dài, lặp ký tự, gõ bừa, mẫu tấn công prompt) rồi đối chiếu danh mục nghiệp vụ (tên bảng/cột có bỏ dấu và đồng nghĩa).
Bị chặn: web/API trả `422` kèm 2–3 ví dụ hợp lệ lấy từ danh mục thật; CLI in khung "Yêu cầu chưa dùng được" và thoát mã 2; không tạo lần chạy, không tốn token, không tính hạn mức.
Câu mà tầng 1 chưa chắc (không thấy từ khóa nghiệp vụ nào) đi tiếp vào graph, node `input_gate` hỏi **bộ phân loại tầng 2** (model riêng `input_gate` ở [config/models.yaml](../config/models.yaml), ≈ 400 token vào, ≤ 30 ra):
`off_topic` chắc ≥ 0,8 → từ chối kèm ví dụ (trạng thái `rejected_input`); `pipeline`/`optimize` còn thiếu ô → hỏi bổ sung bằng **mẫu câu cố định** (LLM không soạn câu hỏi); `unclear`/độ tin cậy thấp → xin viết lại kèm ví dụ, không từ chối thẳng.
Bước hỏi bổ sung dừng ở trạng thái `waiting_input` (web: khung ở bước 1; CLI: nhắc nhập; API: `POST /runs/{id}/input`), tối đa `MAX_CLARIFY_ROUNDS` vòng rồi chuyển cho kỹ sư dữ liệu. Chi phí tầng 2 hiện thành một dòng "Kiểm tra đầu vào" ở bảng token/chi phí.
Chạy thử không cần khóa: tầng 2 dùng luật từ khóa giả lập (`LLM_PROVIDER=mock`); đo bằng model thật: `LLM_PROVIDER=openai python eval/run_input_gate.py` (tốn vài xu).
Cập nhật mẫu chặn: sửa [config/input_gate.yaml](../config/input_gate.yaml). Đo lại: `python eval/run_input_gate.py` (ghi `eval/results/input_gate.md`).
Trần chi phí: `MAX_CLARIFY_ROUNDS`, `RUN_TOKEN_BUDGET`, `USER_DAILY_RUN_LIMIT` (xem [CONFIG](CONFIG.md)); chạm trần thì lần chạy dừng với thông báo tiếng Việt nêu đúng tên biến.

#### Sổ nguồn dữ liệu và mức truy cập của AI

- **Cập nhật cơ sở dữ liệu trước:** `alembic upgrade head` (migration `0005_source_registry` tạo phòng ban, nguồn, quyền xem thêm; seed phòng "Mặc định" và nguồn "P113 Retail" để demo cũ chạy; người dùng cũ vào phòng mặc định). Có Neon: chạy bằng `MIGRATION_DATABASE_URL`.
- **Đăng ký nguồn (Admin, web "Nguồn dữ liệu" hoặc `POST /api/v1/sources`):** chọn phòng ban, loại nguồn, bảng được phép (`*` = mọi bảng), độ nhạy cảm, mức AI được xem. Người thường chỉ thấy nguồn của phòng ban mình; Admin cấp thêm quyền qua `grants`. Gán phòng ban cho người dùng ở trang "Người dùng".
- **Mức AI được xem:** `schema_only` (cấu trúc) < `profile` (thống kê + dạng giá trị, mặc định) < `masked_sample` (vài dòng đã che, chỉ nguồn độ nhạy cảm thấp, Admin bật rõ ràng). Nguồn độ nhạy cảm cao luôn `schema_only`, trung bình tối đa `profile`. Quay về "chỉ cấu trúc" cho nguồn đã đăng ký: `PATCH /sources/{id}` với `llm_access`; cho nguồn mới: `LLM_ACCESS_DEFAULT=schema_only`.
- **Bí mật nguồn:** sổ nguồn chỉ lưu tên tham chiếu (`secret_ref`, vd `conn_orders_db`). Đặt giá trị thật trên máy chủ: biến `P113_SECRET_CONN_ORDERS_DB` (hoặc file cùng tên trong `SECRETS_DIR`). Thiếu thì nguồn đó tạm bị bỏ qua kèm cảnh báo log (các nguồn khác vẫn chạy).
- **Nhật ký truy cập:** `GET /api/v1/admin/audit` (hoặc bảng `audit_log`): `source.list`, `source.create/update/grant/revoke`, `source.ingest`, `llm.context`, `llm_access.downgraded`, `catalog.profile`.
- **Đo:** `python eval/run_llm_access.py` (số token ngữ cảnh từng mức + kiểm rò rỉ, 0 token LLM) ghi `eval/results/llm_access.md`.
- **Người duyệt khác người tạo:** mặc định bật (`REQUIRE_SEPARATE_REVIEWER`); tắt khi demo cá nhân.

#### Thử nguồn PostgreSQL (PostgresConnector, chỉ đọc)

1. Bật PostgreSQL thử: đặt `P113_SOURCES_ADMIN_PASSWORD` trong `.env`, rồi `docker compose --profile dev-sources up -d sources-db` (cổng 127.0.0.1:5434, KHÔNG bật mặc định).
2. Nạp bộ dữ liệu P113 Retail và tạo tài khoản chỉ có quyền SELECT:
   `python scripts/seed_pg_sources.py --dsn postgresql://postgres:<mật khẩu quản trị>@127.0.0.1:5434/p113_retail --reader p113_reader --reader-password <mật khẩu đọc>`.
3. Đặt chuỗi kết nối cho sổ nguồn ở MÁY CHỦ (không nhập vào web): `P113_SECRET_CONN_RETAIL_PG=postgresql://p113_reader:<mật khẩu đọc>@127.0.0.1:5434/p113_retail`, rồi Admin đăng ký nguồn kind=postgres với `secret_ref=conn_retail_pg`, `allowed_tables` (vd `shopee_orders, tiki_orders`) và độ nhạy cảm.
4. Bộ nạp đọc bằng phiên `BEGIN READ ONLY`, kiểm mọi câu lệnh bằng sqlglot trước khi chạy (chỉ một câu SELECT, chỉ bảng được phép), có `statement_timeout` và giới hạn số dòng; dữ liệu chỉ vào sandbox DuckDB của lần chạy (tập con có hạt giống cố định, cột nhạy cảm của nguồn `high` đã băm).
5. Kiểm thử với PostgreSQL thật (CI mặc định bỏ qua): `RUN_PG_TESTS=1 PG_SOURCE_DSN=postgresql://postgres:<mật khẩu>@127.0.0.1:5434/p113_retail python -m pytest tests/test_connectors.py` (không có `PG_SOURCE_DSN` thì dùng `TEST_DATABASE_URL`; tài khoản không được tạo schema thì tạm dùng bảng `customers`/`orders` trong `public` rồi xóa).

#### Từ điển nghiệp vụ (giai đoạn 6)

- **Cập nhật cơ sở dữ liệu:** `alembic upgrade head` (migration `0007_glossary` tạo bảng và seed 17 thuật ngữ P113 Retail từ `config/glossary_seed.yaml`, dùng chung mọi phòng ban).
- **Quản lý:** Admin thêm/sửa ở web "Nguồn dữ liệu" → tab "Từ điển nghiệp vụ" (hoặc `POST/PATCH /api/v1/glossary`). Người khác chỉ đọc. Thuật ngữ gắn phòng ban chỉ người của phòng đó thấy.
- **Viết định nghĩa:** ngắn, rõ, nói điều kiện lọc cụ thể (vd "doanh thu = đơn hoàn tất, không tính đơn hủy/hoàn tiền"). Không ghi giá trị dữ liệu thật. Nếu phần "ứng với" nhắc một bảng người dùng không được thấy thì phần đó bị ẩn (định nghĩa chữ vẫn giữ).
- **Cách dùng:** (1) cửa kiểm tra đầu vào tầng 1 nhận thuật ngữ và từ đồng nghĩa (cụm nhiều chữ hoặc từ đơn ≥ 5 ký tự) làm từ khóa; (2) Planner nhận tối đa `GLOSSARY_MAX_TERMS` thuật ngữ khớp yêu cầu, màn Duyệt kế hoạch (J1b) hiện "Thuật ngữ đã dùng". Tắt: `GLOSSARY_MAX_TERMS=0`.
- **Đo:** `python eval/run_glossary.py` (0 token) ghi `eval/results/glossary.md`: thuật ngữ cần thiết tới được Planner ở 5 ca golden mới (g13–g17), mức tăng token prompt. Độ đúng trước/sau cần LLM thật nên chưa đo; lệnh ở cuối báo cáo.

#### Giám sát thay đổi cấu trúc nguồn (giai đoạn 5)

Hệ thống **phát hiện** khi backend đổi kiểu dữ liệu, đổi tên cột, xóa cột mà không báo; nó **không ngăn được** việc đổi và không tự sửa. Thỏa thuận hợp đồng dữ liệu giữa các đội vẫn là việc của tổ chức.

- **Cập nhật cơ sở dữ liệu:** `alembic upgrade head` (migration `0006_schema_drift`: ảnh chụp cấu trúc, thay đổi, thống kê cơ sở, phụ thuộc pipeline).
- **Bản chuẩn:** lần kiểm đầu tiên của một nguồn (khi có người chạy, bấm "Kiểm tra lại cấu trúc", hoặc lịch định kỳ) đặt cấu trúc lúc đó làm bản chuẩn. Từ đó mọi lệch được ghi thành thay đổi `info` / `warning` / `breaking`.
- **Trước mỗi run (cửa G1, 0 token):** có thay đổi `breaking` đang mở → run dừng ở trạng thái "Chờ xác nhận cấu trúc"; Engineer chọn "Tôi đã biết, dùng cấu trúc mới" (đặt bản chuẩn mới, ghi AuditLog) hoặc dừng. `warning`/`info` cho chạy tiếp và hiện ở màn Duyệt kế hoạch.
- **Trước khi duyệt J2:** kiểm lại; nguồn đổi `breaking` sau lúc sinh code thì cảnh báo đỏ và nút Duyệt bị chặn tới khi chạy lại.
- **Chuông và nút đỏ:** số thay đổi mức "Chặn" đang mở hiện bằng hình oval đỏ trên chuông và cạnh tiêu đề trang "Thay đổi cấu trúc". Mỗi thay đổi có hình so sánh trước/sau (bảng nào, cột nào, đổi gì) và nút "Pipeline cần sửa gì?" chỉ ra file cần sửa (do code phân tích). Nút "Hỏi AI diễn giải thêm" gọi Gemini (`drift_advice`, rẻ, chỉ khi bấm; cần `GOOGLE_API_KEY`, không có thì chỉ hiện phần của code).
- **Số đỏ trên tab:** "Thay đổi cấu trúc" hiện số thay đổi mức Chặn đang mở, "Nguồn dữ liệu" hiện số nguồn có thay đổi chặn (cùng nguồn số liệu với chuông, làm mới mỗi 30 giây). Số chỉ xuất hiện SAU khi hệ thống đã kiểm cấu trúc nguồn (nút "Kiểm tra lại cấu trúc", workflow định kỳ, hoặc cửa G1 trước một lần chạy); hệ thống không tự biết nguồn đổi ngay lúc backend đổi.
- **Trang web "Thay đổi cấu trúc":** danh sách thay đổi, pipeline bị ảnh hưởng, nút "Đề xuất bản vá" mở **kế hoạch vá** (0 token): mỗi thay đổi là một trong "Không cần sửa", "Tự sửa bằng code", "Cần AI", "Cần bạn chọn" (chọn cột thay cho cột đã mất, hoặc bỏ cột khỏi pipeline), "Không vá được" (bảng bị xóa). Bấm "Tạo bản vá" mới tạo run mới; hệ thống không bao giờ tự tạo, tự chạy hay tự merge.
- **Run vá khác run thường ở đâu:** không qua cửa kiểm tra, Planner, hỏi làm rõ, duyệt kế hoạch hay tối ưu; mang đặc tả, câu trả lời và code đã duyệt của lần chạy gốc. Đường ống tiến trình ghi các bước đó "dùng lại từ lần chạy gốc". Bằng chứng ở J2 có hai dòng đo bằng code: số thay đổi đã xử lý (sửa bằng code hay AI, số token) và "So với lần chạy gốc" (bảng đích giống hệt hay khác). Reviewer duyệt xong thì các thay đổi đã vá thành "đã xác nhận" và cấu trúc mới thành bản chuẩn (số đỏ giảm).
- **Thử trên bản deploy:** đăng ký một nguồn PostgreSQL thử (chỉ đọc), tạo và chạy xong một pipeline dùng bảng đó, rồi đổi cấu trúc bảng ở nguồn (`ALTER TABLE ... RENAME COLUMN ...`, `ALTER COLUMN ... TYPE text`, `DROP COLUMN ...`). Bấm "Kiểm tra lại cấu trúc" (hoặc chạy tay workflow `drift-check`), rồi xem số đỏ, hình so sánh và kế hoạch vá. Cần `DRIFT_GATE_ENABLED=true` nếu muốn cửa G1 chặn run mới.
- **Xem thử cục bộ không cần nguồn thật:** `python demo/seed_drift.py` (khi demo đang chạy) tạo 5 thay đổi giả trên nguồn "P113 Retail" để xem số đỏ, hình so sánh và kế hoạch vá; kiểm tra lại cấu trúc sẽ đánh dấu chúng là đã hết vì file nguồn thật không đổi.
- **Đo bản vá nhanh:** `python eval/run_patch.py` (mock, 0 token, ghi `eval/results/patch.md`); thêm `--with-llm` để Codegen/Testgen của kịch bản cần AI gọi LLM thật (khoảng 8 nghìn token, dưới 0,01 USD với `gpt-6-luna`; cần khóa trong `.env`), ghi `eval/results/patch_llm.md`.
- **Kiểm tra định kỳ:** đặt `DRIFT_CHECK_TOKEN` (chuỗi ngẫu nhiên dài) ở máy chủ API, và hai secret của repo GitHub: `DRIFT_CHECK_URL` (vd `https://api.congty.vn`) cùng `DRIFT_CHECK_TOKEN` (cùng giá trị). Workflow `.github/workflows/drift-check.yml` gọi `POST /api/v1/sources/check-drift` hằng ngày (cũng chạy tay được); có thể thay bằng bộ lập lịch khác gọi cùng endpoint với header `X-Drift-Token`.
- **Pipeline sinh ra tự phòng thủ:** khai báo nguồn dbt (`models/sources.yml`: cột, kiểu, `not_null`/`unique`/`accepted_values`/`freshness`), macro `check_source_schema` chạy trước mọi task (DAG có task đầu tiên gọi nó), không `SELECT *` ở staging/mart, test đếm dòng không ép được kiểu (ngưỡng `CAST_FAIL_THRESHOLD`).
- **Mô phỏng 6 kịch bản "backend đổi không báo":** `python scripts/simulate_drift.py` (0 token, ghi `eval/results/drift.md`).

### 2.3 Duyệt (bước con người J2)

```powershell
python -m src.cli review 8ff0c55055                                    # xem rồi chọn approve / reject
python -m src.cli review latest --full                                 # lần chạy mới nhất, xem đủ nội dung file
python -m src.cli review latest --reject --note "thêm cột nguồn"
```

Màn duyệt có: đặc tả bằng lời, bảng **"Code đo | LLM nói"**, kết quả mẫu, báo cáo tối ưu (thời gian trước/sau,
quyết định `applied`/`skipped`), diff code. Từ chối → agent sửa lại theo ghi chú rồi chờ duyệt lần nữa.

Luật duyệt: chỉ vai trò **Reviewer** được duyệt hoặc từ chối (`--as reviewer`, mặc định của lệnh `review`); Engineer
tạo yêu cầu (`--as engineer`, mặc định của `run`). Reviewer được duyệt cả yêu cầu do chính mình tạo.

### 2.4 Lệnh khác

| Lệnh | Việc |
|---|---|
| `python -m src.cli status` | Danh sách lần chạy |
| `python -m src.cli status <run_id>` | Chi tiết một lần chạy (provider, token, chi phí, workspace) |
| `python -m src.cli answer <run_id>` | Trả lời câu hỏi làm rõ cho lần chạy đang chờ |
| `python -m src.cli errors` | Sổ lỗi chờ duyệt; `--approve <id> --fix "cách sửa"` để duyệt |
| `python -m src.cli optimize --sql query.sql --dataset large` | Chạy riêng Optimizer + Đối chiếu cho một file SQL |
| `python -m src.cli --provider openai run ...` | Dùng LLM thật cho lần chạy này (cần khóa, xem mục 5) |

Code sinh ra nằm ở `pipelines/workspaces/<run_id>/` (dự án dbt, DAG, test, `PULL_REQUEST.md`).

### 2.5 Kịch bản demo trọn vẹn (để quay video/chụp màn hình)

```powershell
python scripts/tasks.py demo         # seed → Engineer "an" tạo yêu cầu → Reviewer "binh" duyệt
```

Ví dụ đầu ra thật (mock, máy Windows):

```
 ✓ E1 Lập kế hoạch        0.13s   bảng đích fct_daily_revenue, mode ELT
 ✗ V0 Soát đặc tả         0.00s   Còn 2 điểm chưa rõ: ...
 ✓ J1 Hỏi làm rõ          0.00s
 ✓ V0 Soát đặc tả         0.00s   đạt
 ✓ E0 Nhận nguồn          5.13s   shopee_orders: 315 dòng, tiki_orders: 300 dòng, website_orders: 300 dòng
 ✓ V1 An toàn             0.11s   không phát hiện vấn đề
 ✓ V2 Chạy sandbox        7.86s   1/1 model, 6/6 test đạt
 ✓ E4 Tối ưu              4.09s   2 dấu hiệu chậm, baseline 333.042 ms, đã có đề xuất
 ✓ V3 Đối chiếu           1.60s   applied: Nhanh hơn 44.6% (≥ 15.0%), kết quả giống hệt trên mọi bộ dữ liệu.
 ...
Trạng thái: đã duyệt
```

Con số tối ưu là **đo thật** trên bộ dữ liệu `large` giả lập của máy bạn nên mỗi lần chạy sẽ khác một chút
(đã thấy 21%–45% trên cùng máy). Chế độ mock chỉ cố định phần câu trả lời LLM, không cố định số đo.

## 3. Chạy web trên máy

Cần thêm **Node.js 20.9 trở lên** (kiểm tra: `node --version`). Mở 2 cửa sổ terminal:

```powershell
# Cửa sổ 1 — API
python scripts/tasks.py run              # make run → http://localhost:8000/docs
# Cửa sổ 2 — giao diện (lần đầu: cd frontend; npm ci; cd ..)
python scripts/tasks.py frontend-dev     # make frontend-dev → mở http://localhost:3000
```

Cách dùng (một DE làm từ đầu đến cuối):
1. **Lần chạy** → gõ yêu cầu (hoặc bấm ví dụ) → **Tạo pipeline**.
2. Agent dừng ở **J1** nếu cần làm rõ → chọn đáp án → **Gửi câu trả lời**.
3. Agent trình bày **kế hoạch** (J1b): tóm tắt, từng bước kèm "Vì sao", đặc tả → **Đồng ý, sinh code**, hoặc ghi
   chú rồi **Yêu cầu sửa kế hoạch**.
4. Khi trạng thái là **Chờ duyệt** → tab **Duyệt code**: xem từng file, bằng chứng "Code đo | LLM nói" → **Duyệt**,
   hoặc ghi chú rồi **Từ chối** (agent sửa và quay lại chờ duyệt, lúc này thấy diff với bản cũ).
5. Tab **Cấu trúc dữ liệu**: sơ đồ bảng raw → staging → mart, bấm vào bảng để xem schema, quan hệ, khóa nối.
6. Duyệt xong → **Tải gói code (.zip)** → chép vào repo dbt của đội → mở Pull Request để CI/CD chạy.

Mở web sẽ vào trang **Đăng nhập** (tài khoản do Admin cấp; tạo mẫu cho dev: `python -m src.cli users seed-dev`).
Avatar góc phải: tên, vai trò, giao diện sáng/tối, nhãn **Mô phỏng**/**LLM thật**, nút **Đăng xuất** (phiên mất hiệu lực
ở máy chủ ngay). Nút của vai trò khác bị khóa kèm lời nhắc; backend vẫn chặn (403). Admin có thêm mục **Người dùng**:
cấp tài khoản, đổi vai trò, khóa/mở, đặt lại mật khẩu (mọi phiên của người đó bị thu hồi).

Web và CLI dùng chung kho dữ liệu `data/` khi chạy bằng `make run`: lần chạy tạo ở terminal cũng thấy trên web.

**Docker** (mở Docker Desktop trước):

```powershell
docker compose up --build -d             # web http://localhost:3000 • API http://localhost:8000/health
docker compose down                      # tắt (dữ liệu vẫn giữ trong volume)
docker compose down -v                   # tắt và xóa sạch dữ liệu của bản Docker
```

- docker compose đọc `LLM_PROVIDER` trong `.env`. Đang để `openai` thì bản Docker **dùng LLM thật và tốn phí**.
  Muốn thử miễn phí: `$env:LLM_PROVIDER="mock"; docker compose up --build -d`.
- Dữ liệu bản Docker nằm trong volume riêng, không dùng chung `data/` trên máy (SQLite chế độ WAL không ghi an toàn
  qua thư mục Windows gắn vào container). Lần đầu chạy API tự sinh dữ liệu mẫu.
- Đổi địa chỉ API cho web: `NEXT_PUBLIC_API_URL` (được nhúng lúc build, đổi xong phải build lại).

Giới hạn bản demo: các lần chạy xếp hàng **lần lượt** (một luồng nền); tiến trình từng bước giữ trong bộ nhớ nên mất
khi khởi động lại API (trạng thái và kết quả vẫn còn); trình xem code Monaco tải từ CDN nên máy cần có mạng.

## 4. Kiểm thử

```powershell
python scripts/tasks.py test         # pytest + độ phủ (ngưỡng 60%)
python scripts/tasks.py ci           # giống hệt GitHub Actions: ruff check → ruff format --check → pytest
```

Test không cần khóa API, không cần mạng. Mất khoảng 1,5–2 phút vì có test chạy dbt thật trong sandbox.

### 4.1 Đánh giá (Phase 6)

```powershell
python scripts/tasks.py eval         # hoặc: make eval  •  python -m src.cli eval
python scripts/tasks.py eval-llm     # thêm bộ golden chạy bằng LLM thật (tốn token, cần khóa)
```

Kết quả ở `eval/results/report.md` (chỉ ghi số đo thật, kèm provider/model). `make eval` gồm:

| Phần | Đo gì | Cần LLM? |
|---|---|---|
| pytest + độ phủ | Code chạy đúng | Không |
| Golden reference (`eval/datasets/golden/`, 12 ca) | Kết quả đúng tính tay khớp câu SQL chuẩn | Không |
| Mutation (`eval/mutation/mutants.yaml`) | Cấy lỗi giả (SUM→AVG, bỏ WHERE, bỏ khử trùng, đọc sai ngày/tiền...) → V1/V2 có bắt được không | Không |
| Golden agent (`eval-llm`) | Agent làm đúng bao nhiêu ca, hỏi làm rõ khi mơ hồ, chọn đúng ELT/ETL, token, thời gian | Có |

Trên GitHub: tab **Actions → Eval → Run workflow** (chạy phần không cần LLM, tải kết quả ở mục Artifacts).

### 4.2 Benchmark

- TPC-H (đo tốc độ Optimizer, cần mạng lần đầu): `python eval/benchmarks/tpch/run_tpch.py --sf 0.1`
- ELT-Bench (đo độ đúng toàn luồng): xem [eval/benchmarks/README.md](../eval/benchmarks/README.md).

## 5. Bật LLM thật (khi có khóa)

1. Lấy khóa ở <https://platform.openai.com/api-keys> và <https://console.anthropic.com> (cả hai cần nạp tiền; xem `docs/guide/cost-management.md`).
   Khóa dự phòng Gemini (không bắt buộc): <https://aistudio.google.com/apikey>.
2. Mở file `.env` bằng trình soạn thảo, **tự điền**: `OPENAI_API_KEY=<khóa của bạn>`, `ANTHROPIC_API_KEY=<khóa>`, `GOOGLE_API_KEY=<khóa>` (nếu có)
   và `LLM_PROVIDER=openai`. Không dán khóa vào chat, không commit `.env`.
3. `python -m src.cli doctor` → dòng LLM và "LLM dự phòng" phải là ✓.
4. Chạy lại `run`. Token và chi phí ước tính hiện ở `python -m src.cli status <run_id>`.

Model theo từng bước: sửa [config/models.yaml](../config/models.yaml) (không đặt trong `.env`).

| Bước | Model hiện tại | Khóa cần |
|---|---|---|
| Planner, Codegen, Testgen | `gpt-5.6-luna` | `OPENAI_API_KEY` |
| Optimizer (viết lại query chậm) | `claude-haiku-5-5` (không đặt effort) | `ANTHROPIC_API_KEY` (<https://console.anthropic.com>) |
| Dự phòng (`LLM_FALLBACK=google`) | `gemini-3.1-flash-lite` | `GOOGLE_API_KEY` |

`LLM_PROVIDER=google` dùng Gemini cho mọi bước. Chạy một lần bằng mô phỏng: `python -m src.cli --provider mock run ...`.

Thiếu khóa mà chọn `openai`, hệ thống báo bằng tiếng Việt phải làm gì, không dừng đột ngột.

## 6. Deploy

Hai hướng dẫn từng bước (kèm kiểm tra sau deploy, lỗi thường gặp, cách gỡ để không tốn tiền):

- [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md): frontend trên Vercel, backend trên Render (hoặc Railway), PostgreSQL trên Neon.
- [DEPLOY_GCP.md](DEPLOY_GCP.md): Cloud Run + Cloud SQL + Secret Manager.

Tình trạng: tài liệu đã viết, **chưa deploy thật** (chưa có Live URL).

## 7. Đẩy code lên GitHub

```powershell
git status                           # KHÔNG được thấy .env trong danh sách
bash scripts/setup_hooks.sh          # một lần (hoặc: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1)
git switch -c feature/<ten-viec>
git add <file>
git commit -m "feat: mô tả ngắn"
git push -u origin feature/<ten-viec>
```

Mở Pull Request vào `main` trên GitHub, đợi tab **Actions** xanh rồi merge. Hook gửi AI log lên server chấm khi push,
mỗi thành viên cần `AI_LOG_API_KEY` riêng trong `.env`.

## 8. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `Chưa có nguồn dữ liệu trong data/sources` | Chạy `python -m src.cli seed` |
| `LLM_PROVIDER=openai nhưng chưa có OPENAI_API_KEY` | Điền khóa vào `.env` hoặc đổi `LLM_PROVIDER=mock` |
| `llm primary failed, using fallback` trong log | OpenAI lỗi tạm thời, đã tự chuyển sang Gemini; nếu lặp lại thường xuyên thì kiểm tra hạn mức OpenAI |
| Chữ tiếng Việt lỗi trong terminal | Dùng PowerShell/Windows Terminal; hoặc chạy `$env:PYTHONIOENCODING="utf-8"` |
| `make` không tồn tại (Windows) | Dùng `python scripts/tasks.py <đích>` |
| Cổng 8000 bị chiếm | `python -m uvicorn src.main:app --port 8001` (web: đặt `NEXT_PUBLIC_API_URL=http://localhost:8001`) |
| Web báo "Không kết nối được máy chủ API" | Kiểm tra API đang chạy (`/health`); đúng `NEXT_PUBLIC_API_URL`; địa chỉ web nằm trong `CORS_ORIGINS` |
| Lần chạy dừng "Có lỗi nội bộ", V2 báo dbt dừng không in kết quả, web báo "Chưa có nhật ký từng bước" | Máy chủ API đã khởi động lại giữa lần chạy. Chạy API bằng `python scripts/tasks.py run` (đã có `--reload-dir src`); nếu tự gõ lệnh uvicorn với `--reload` thì thêm `--reload-dir src`, vì V2 ghi file `.py` vào `pipelines/workspaces/`. Chi tiết lỗi in ở cửa sổ terminal chạy API (không ghi ra file) |
| Cổng 3000 bị chiếm | Tắt server web cũ, hoặc `npm --prefix frontend run dev -- -p 3001` và thêm `http://localhost:3001` vào `CORS_ORIGINS` |
| Docker báo không kết nối được daemon | Mở Docker Desktop, đợi biểu tượng chuyển xanh |
| `dbt build vượt quá thời gian cho phép` | Tăng `SANDBOX_TIMEOUT_SEC` trong `.env` |
| Lần chạy dừng ở "chờ cứu hộ" | Agent sửa 3 lần không được (hoặc lặp cùng lỗi 2 lần): nhập gợi ý cho agent hoặc bỏ trống để dừng |
