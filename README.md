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

Chạy giao diện web (cần PostgreSQL cho đăng nhập) và các cách khác: [docs/RUNBOOK.md](docs/RUNBOOK.md), [docs/DATABASE.md](docs/DATABASE.md).

## Kết quả

Chi tiết và điều kiện đo: [eval/results/report.md](eval/results/report.md) (sinh 2026-10-10). `mock` không phản ánh chất lượng mô hình thật.

| Chỉ số | Điều kiện đo | Kết quả |
|---|---|---|
| Golden 12 ca: agent đúng | LLM thật (gpt-5.6-luna/terra), 1 lần, 2026-10-08 | **12/12**, ~46 giây và ~0,0045 USD mỗi ca |
| Mutation: bắt lỗi giả | code, 0 token | **11/12** (91,7%), báo nhầm 0/1 |
| TPC-H sf=0,1: query chậm được tối ưu | `mock`, 2026-10-02 | **11/13**, nhanh hơn 51%–94,7%, 10/11 không tốn token |
| ELT-Bench-Verified: khớp bảng đúng | LLM thật, 34 bảng, 1 lần, chấm lại 2026-10-07 | **11/34** (gồm 2 model lỗi của benchmark) |
| Test tự động | `mock`, độ phủ ngưỡng 60% | 626 passed, độ phủ 91,76% |
| Thời gian phản hồi API | trong tiến trình, SQLite, 100 lần | p50 2,2 ms, p95 4,3 ms (`/health`) • [api_latency.md](eval/results/api_latency.md) |

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [BAO_CAO](docs/BAO_CAO.md) | Báo cáo cho người không chuyên: bài toán, J-E-V, thuật toán, số đo |
| [DATABASE](docs/DATABASE.md) | PostgreSQL, SQLite, DuckDB; dựng từ đầu, xem dữ liệu, sao lưu |
| [DEPLOY_VERCEL](docs/DEPLOY_VERCEL.md) • [DEPLOY_GCP](docs/DEPLOY_GCP.md) | Hai cách deploy (chưa chạy thật) |
| [RUNBOOK](docs/RUNBOOK.md) | Chạy, kiểm thử, bật LLM thật, lỗi thường gặp |
| [ARCHITECTURE](ARCHITECTURE.md) • [ADR](docs/adr/) | Kiến trúc và các quyết định |
| [API](docs/API.md) • [CONFIG](docs/CONFIG.md) | Danh sách endpoint; biến môi trường |
| [WORKLOG](WORKLOG.md) • [JOURNAL](JOURNAL.md) • [CONTRIBUTING](CONTRIBUTING.md) | Nhật ký công việc, bài học, quy tắc đóng góp và ghi log AI |

## Hạn chế thật

- Chạy trên **kho dữ liệu giả lập** "P113 Retail" ([docs/data-catalog.md](docs/data-catalog.md)), chưa thử với dữ liệu công ty thật.
- **Chưa có DE làm tay** để so thời gian ([quy trình](eval/baseline/PROTOCOL.md)); mỗi phép đo chạy 1 lần; nhãn kiểm thử do tác giả gán.
- Lần chạy, quyết định duyệt, sổ lỗi và checkpoint còn ở **SQLite** nên backend chỉ chạy một bản, cần ổ đĩa bền ([DATABASE.md](docs/DATABASE.md)).
- Chưa deploy thật; chưa có phản hồi người dùng thử; sandbox chỉ DuckDB, gợi ý partition cho kho khác không được thực thi.
- Trình xem code Monaco tải từ CDN jsDelivr nên cần mạng.

## Deliverables

- [x] Source code • [x] README • [x] Sơ đồ kiến trúc • [x] AI logs • [x] Weekly journal • [x] Worklog • [x] Evidence ([report.md](eval/results/report.md))
- [ ] Live URL / Deploy • [ ] Video demo ([kịch bản](docs/video-demo.md)) • [ ] Pitch deck ([dàn ý](presentation/outline.md))

## Team

| Member | Role | Student ID |
|--------|------|-----------|
| TrungTuyenDo02 | Toàn bộ hệ thống | — |

## License

[MIT](LICENSE)
