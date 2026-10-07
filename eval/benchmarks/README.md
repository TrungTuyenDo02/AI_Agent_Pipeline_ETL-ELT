# eval/benchmarks — đo tốc độ Optimizer (E4) + Đối chiếu (V3)

## TPC-H (`tpch/`)

13 truy vấn TPC-H viết chậm cố ý (`tpch/slow/*.sql`, lấy từ nhánh `feature/optimizer-agent`). Mỗi file có header
`-- reference: tpch:<n>` (đáp án đúng = truy vấn chuẩn TPC-H số n) và `-- pattern:` mô tả lỗi cố ý.
Các file ghi "(đối chứng)" là ca DuckDB tự tối ưu được — kết quả `skipped` ở đó là đúng thiết kế.

```powershell
python eval/benchmarks/tpch/run_tpch.py --sf 0.1     # nhanh (~1 phút); --sf 1 để đo sát thực tế hơn
```

- Lần đầu cần mạng: DuckDB tải extension `tpch`. Vì vậy **không chạy trong CI**.
- Dữ liệu sinh vào `data/tpch_sf<sf>.duckdb` (git-ignored; sf=0.1 ≈ 30 MB, sf=1 ≈ 300 MB).
- Kết quả: `eval/results/tpch_benchmark.md` (ghi rõ provider/model; số đo thật).

## ELT-Bench-Verified (`eltbench/`)

Đo độ đúng của **toàn bộ luồng** (yêu cầu bằng lời → dbt → kết quả) trên bài toán ELT công khai.
Nguồn: ELT-Bench-Verified (IBM Research / ETH Zürich / UIUC), giấy phép **CC BY-SA 4.0**,
<https://github.com/czanoli/ELT-Bench> nhánh `elt-bench-pr`.

| Lấy | Bỏ |
|---|---|
| Bảng nguồn thô, yêu cầu (`data_model.yaml`), bảng kết quả đúng (`gt_verified`), câu kiểm tra (`evaluation/`) | Airbyte, Terraform, cấu hình Snowflake (hệ thống chạy DuckDB local) |

- `tasks.yaml`: 10 pipeline nhẹ nhất (2–22 KB, tổng 34 model) trong 95/100 task có đủ dữ liệu và bảng kết quả đúng.
- `reference/cs_semester/*.sql`: model dbt chuẩn (viết tay ở nhánh `feature/optimizer-agent`, đã khớp bảng đúng).
  Benchmark gốc chỉ có SQL chuẩn cho `retails`; các task khác chấm bằng bảng kết quả đúng.
- Kiểu dữ liệu giữ như Airbyte nạp: CSV từ postgres/mongodb/API → Parquet có kiểu; CSV từ S3 → chuỗi; jsonl/parquet giữ nguyên.

Dữ liệu đã có sẵn trong repo ở `eval/datasets/eltbench/` (~700 KB, xem README trong đó về giấy phép).
Không cần tải thêm.

```powershell
# 0) Tự kiểm bộ chấm: chấm 34 bảng đúng như đầu ra agent → phải 34/34 (không cần LLM; CI chạy qua pytest,
#    kèm kiểm ngược: đổi 1 ô ở mỗi bảng đúng → phải bắt được 34/34)
python eval/benchmarks/eltbench/run_eltbench.py --mode selfcheck
# 1) Kiểm chứng bộ chấm bằng model chuẩn (không cần LLM; CI cũng chạy ca này qua pytest)
python eval/benchmarks/eltbench/run_eltbench.py --mode reference
# 2) Chấm agent: mỗi model một lần chạy trọn luồng (cần khóa LLM thật); đầu ra lưu ở eval/results/eltbench_runs/<đợt>/
python eval/benchmarks/eltbench/run_eltbench.py --mode agent --provider openai
# 3) Chấm lại một đợt đã lưu bằng bộ chấm hiện tại (0 token)
python eval/benchmarks/eltbench/run_eltbench.py --regrade 2026-10-02_1327
# (Tùy chọn) Tạo lại dữ liệu từ bản tải về — chỉ ĐỌC thư mục tải về
python eval/benchmarks/eltbench/import_eltbench.py --src "<thư mục chứa ELT-Bench-Verified và eltbench_raw>"
```

Kết quả: `eval/results/eltbench_selfcheck.md`, `eval/results/eltbench_reference.md`, `eval/results/eltbench_agent.md`
(đợt chấm gần nhất) và `eval/results/eltbench_runs/<đợt>/report.md`. Mỗi model của đợt có `output.parquet` (bảng đích),
`models/` (SQL dbt agent sinh), `meta.json` (trạng thái, token, chi phí, run_id).
Lỗi của chính benchmark (đề yêu cầu cột mà bảng đúng không có) ghi ở `eltbench/known_issues.yaml`; báo cáo in hai số
**gồm** / **không gồm** các model đó, và số dòng bảng đúng (`gt_rows`; bảng ≤ 5 dòng → tin cậy thấp).
Đợt 2026-10-02 chạy trước khi có B2: đầu ra lấy lại từ workspace bằng `eltbench/backfill_runs.py` (một lần).
Ghi chú: agent dựng **một bảng đích mỗi lần chạy**, nên mỗi model của task là một lần chạy riêng.
Câu hỏi làm rõ (J1) trong eval được chọn đáp án đầu tiên và **đếm lại** (`auto_answers`) để không che giấu.
