# P-113 — Agent viết và tối ưu pipeline ELT/ETL

[![CI](https://github.com/TrungTuyenDo02/AI_Agent_Pipeline_ETL-ELT/actions/workflows/ci.yml/badge.svg)](https://github.com/TrungTuyenDo02/AI_Agent_Pipeline_ETL-ELT/actions/workflows/ci.yml)

> Nói bằng lời bạn cần bảng dữ liệu gì → agent sinh dbt + DAG Airflow, chạy thử trong sandbox, đo và tối ưu query, rồi **chờ người duyệt** trước khi merge.

**Live URL:** chưa có (chưa deploy) • **Video demo:** chưa có ([kịch bản](docs/video-demo.md)) • **Báo cáo:** [docs/BAO_CAO.md](docs/BAO_CAO.md)

## Demo

Chụp ở chế độ mô phỏng (`LLM_PROVIDER=mock`), dữ liệu giả lập.

| Duyệt kế hoạch (J1b), trước khi sinh code | Duyệt code: bằng chứng "Code đo \| LLM nói" |
|---|---|
| ![Duyệt kế hoạch](docs/screenshots/web_plan_review.png) | ![Duyệt code](docs/screenshots/web_review.png) |

## Vấn đề → Giải pháp

DE mất nhiều giờ viết lặp staging, mart, test, DAG; dữ liệu bẩn (đơn trùng, ngày lẫn định dạng, tiền `1.075.000`) làm sai số; trợ lý sinh code thường không chạy thử mà vẫn báo "xong".
Nguyên tắc **J-E-V**: người **phán đoán** (J), agent **thực thi** (E), code thuần **kiểm chứng** (V, 0 token).

- **Hỏi trước khi làm:** Planner hỏi trắc nghiệm khi còn điểm chưa rõ, rồi trình kế hoạch có giải thích để DE duyệt.
- **Sinh đầy đủ:** model dbt, DAG Airflow, test đối soát do một agent khác viết **không nhìn code**.
- **Kiểm chứng bằng code:** sqlglot chặn lệnh nguy hiểm và tên bảng/cột bịa; `dbt build` trong DuckDB có giới hạn thời gian và bộ nhớ.
- **Tối ưu có đo:** luật cố định → sqlglot → LLM; chỉ áp dụng khi kết quả **giống hệt** và nhanh hơn ngưỡng.
- **Hợp đồng bàn giao cố định:** dữ liệu giữa các node đi qua khuôn Pydantic ([src/models/contracts.py](src/models/contracts.py)), sai trường hay kiểu thì báo ngay ở node gây ra.
- **Duyệt có bằng chứng:** Reviewer thấy diff và bảng "Code đo | LLM nói"; agent không tự đẩy code.

## Kiến trúc

![Sơ đồ kiến trúc P-113](docs/adr/architecture.png)

Mô tả từng khối: [ARCHITECTURE.md](ARCHITECTURE.md) • sơ đồ Mermaid: [docs/architecture_diagram.md](docs/architecture_diagram.md).
Stack: LangGraph, FastAPI, dbt + DuckDB, sqlglot, Next.js 16, PostgreSQL 17 + Alembic, Docker, GitHub Actions.

## Chạy thử trong 5 phút (mô phỏng, không cần khóa)

```bash
git clone https://github.com/TrungTuyenDo02/AI_Agent_Pipeline_ETL-ELT.git && cd AI_Agent_Pipeline_ETL-ELT
python -m venv .venv && source .venv/bin/activate       # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt && cp .env.example .env # Windows: Copy-Item .env.example .env
python scripts/tasks.py demo                            # chạy trọn luồng trong terminal: yêu cầu → duyệt
python scripts/tasks.py ci                              # ruff + pytest (độ phủ ≥ 60%)
```

### Chạy giao diện web (demo một lệnh, không cần PostgreSQL, không cần khóa API)

```bash
cd frontend && npm ci && cd ..      # một lần
python demo/run_demo.py             # build + chạy; mở http://localhost:3000
```

Trang đăng nhập có khung giới thiệu dự án, hướng dẫn chạy, mô tả dữ liệu mẫu và 3 tài khoản demo (bấm để điền sẵn); có nút VI/EN và sáng/tối.
Chi tiết: [demo/README.md](demo/README.md). Các cách chạy khác: [docs/RUNBOOK.md](docs/RUNBOOK.md), [docs/DATABASE.md](docs/DATABASE.md).

### Lưu trạng thái trên Neon (triển khai thật)

Mặc định (`STATE_BACKEND=sqlite`) lần chạy, sổ lỗi, bộ nhớ agent và checkpoint nằm trong file SQLite ở `data/`. Đặt `STATE_BACKEND=postgres`
để lưu tất cả trên PostgreSQL/Neon (Render xóa ổ đĩa khi khởi động lại), chạy `alembic upgrade head`, và tăng `RUN_WORKERS` (mặc định 2) để
chạy nhiều lần cùng lúc. Xem [docs/DATABASE.md](docs/DATABASE.md), [.env.production.example](.env.production.example).

## Kết quả

Chi tiết và điều kiện đo: [eval/results/report.md](eval/results/report.md) (sinh 2026-10-10). `mock` không phản ánh chất lượng mô hình thật.

| Chỉ số | Điều kiện đo | Kết quả |
|---|---|---|
| Golden 12 ca: agent đúng | LLM thật (gpt-5.6-luna/terra), 1 lần, 2026-10-08 | **12/12**, ~46 giây và ~0,0045 USD mỗi ca |
| Mutation: bắt lỗi giả | code, 0 token | **11/12** (91,7%), báo nhầm 0/1 |
| TPC-H sf=0,1: query chậm được tối ưu | `mock`, 2026-10-02 | **11/13**, nhanh hơn 51%–94,7%, 10/11 không tốn token |
| ELT-Bench-Verified: khớp bảng đúng | LLM thật, 34 bảng, 1 lần, chấm lại 2026-10-07 | **11/34** (gồm 2 model lỗi của benchmark) |
| Optimizer: model LLM nào tốt hơn | LLM thật, chỉ ứng viên do LLM viết, 13 query, 1 lần, 2026-10-14 | Claude Haiku 4.5 **9/13** bản đúng và nhanh hơn, 0,083 USD; gpt-5.6-terra 5/13, 0,24 USD; Claude Opus 5.5 3/13, 0,96 USD • [ab_optimizer.md](eval/results/ab_optimizer.md) |
| Baseline: truy vấn viết tay không tối ưu = 100% | `mock` (luật cố định + sqlglot), sf=0,1, 1 lần, 2026-10-14 | cả bộ còn **14%** thời gian, **86%** dòng quét; chi phí tính toán ước tính (giả định) cũng còn 14% • [tpch_baseline.md](eval/results/tpch_baseline.md) |
| Test tự động | `mock`, độ phủ ngưỡng 60% | 717 passed, 2 xfailed, độ phủ 92,13% (2026-10-14) |
| Thời gian phản hồi API | trong tiến trình, SQLite, 100 lần | p50 2,2 ms, p95 4,3 ms (`/health`) • [api_latency.md](eval/results/api_latency.md) |

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [BAO_CAO](docs/BAO_CAO.md) | Báo cáo cho người không chuyên: bài toán, J-E-V, thuật toán, số đo |
| [DATABASE](docs/DATABASE.md) | PostgreSQL/Neon, SQLite, DuckDB; dựng từ đầu, xem dữ liệu, sao lưu |
| [DEPLOY_VERCEL](docs/DEPLOY_VERCEL.md) • [DEPLOY_GCP](docs/DEPLOY_GCP.md) | Hai cách deploy (chưa chạy thật) |
| [RUNBOOK](docs/RUNBOOK.md) | Chạy, kiểm thử, bật LLM thật, lỗi thường gặp |
| [ARCHITECTURE](ARCHITECTURE.md) • [ADR](docs/adr/) | Kiến trúc và các quyết định |
| [API](docs/API.md) • [CONFIG](docs/CONFIG.md) | Danh sách endpoint; biến môi trường |
| [WORKLOG](WORKLOG.md) • [JOURNAL](JOURNAL.md) • [CONTRIBUTING](CONTRIBUTING.md) | Nhật ký công việc, bài học, quy tắc đóng góp và ghi log AI |

## Hạn chế thật

- Chạy trên **kho dữ liệu giả lập** "P113 Retail" ([docs/data-catalog.md](docs/data-catalog.md)), chưa thử với dữ liệu công ty thật.
- **Chưa có DE làm tay** để so thời gian ([quy trình](eval/baseline/PROTOCOL.md)); mỗi phép đo chạy 1 lần; nhãn kiểm thử do tác giả gán.
- Đã hỗ trợ lưu trên **Neon** (kiểm thử trên nhánh dev: 2 lần chạy song song), nhưng chưa deploy và chưa đo tải thật trên Render; bộ nhớ dài hạn của agent mới có bảng và dịch vụ, chưa nối vào prompt.
- **ELT-Bench chỉ 11/34 bảng** và có ca được duyệt nhưng sai; golden 12/12 chưa tách tập kiểm riêng; mutation test dùng bộ sinh test giả (`mock`); tối ưu TPC-H "viết tay → tối ưu" đo bằng luật cố định, phần LLM chỉ có phép đo A/B nhỏ ở trên (13 query, 1 lần mỗi model).
- Chưa deploy thật; chưa có phản hồi người dùng thử; sandbox chỉ DuckDB, gợi ý partition cho kho khác không được thực thi.
- Trình xem code Monaco tải từ CDN jsDelivr nên cần mạng.

## Deliverables

- [x] Source code • [x] README • [x] Sơ đồ kiến trúc • [x] AI logs • [x] Weekly journal • [x] Worklog • [x] Evidence ([report.md](eval/results/report.md))
- [ ] Live URL / Deploy • [ ] Video demo ([kịch bản](docs/video-demo.md)) • [ ] Pitch deck ([dàn ý](presentation/outline.md))

## License

[MIT](LICENSE)
