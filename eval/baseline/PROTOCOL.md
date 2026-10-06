# Mốc "DE làm tay" — quy trình đo

Mục đích: có số thật để so thời gian của agent với một Data Engineer làm cùng việc. Chưa có người làm thì
báo cáo ghi `—`, không ước lượng thay.

## 1. Người làm

- Một Data Engineer biết dbt và SQL. Ghi **số năm kinh nghiệm** (làm tròn, ví dụ `2`).
- Không phải người viết bộ golden (người viết đã biết đáp án).
- Mục tiêu: **ít nhất 1 DE, 5–10 ca**. Nhiều DE làm cùng ca thì báo cáo lấy trung vị.

## 2. Đầu vào (giống hệt agent)

Với mỗi ca `eval/datasets/golden/<case_id>/`, DE chỉ được nhận:

- `request.txt`: yêu cầu bằng lời, đúng câu agent nhận.
- `sources/`: dữ liệu nguồn, đúng file agent nhận.

**Không đưa** `reference.sql`, `expected.csv`, `meta.yaml` (đó là đáp án và bẫy của ca).

Ca `g10_ambiguous_request` là yêu cầu mơ hồ. DE được hỏi lại người giao việc. Người giao việc trả lời theo
`clarify_prefer` trong `meta.yaml`, giống cách eval trả lời agent. Thời gian chờ câu trả lời **không** tính.

## 3. Việc phải làm (cùng mốc với agent)

Agent dừng đồng hồ khi có **bản duyệt**: model dbt (staging + bảng đích), test, một DAG Airflow, đã chạy thử
đạt. DE làm cùng mức đó:

1. Model dbt chạy trên DuckDB: staging cho từng nguồn và bảng đích đúng tên, đúng cột như yêu cầu.
2. Ít nhất một test: khóa không trùng hoặc không rỗng.
3. Một file DAG Airflow gọi `dbt build` (không cần chạy Airflow thật).
4. `dbt build` chạy đạt trên dữ liệu `sources/`.

Được dùng: tài liệu, Google, code mẫu của chính mình. **Không** dùng trợ lý AI sinh code (ghi rõ vào
`ghi_chú` nếu có dùng; dòng đó báo cáo tách riêng).

## 4. Bấm giờ

- **Bắt đầu:** lúc DE mở `request.txt`.
- **Dừng:** lúc DE thấy đã sẵn sàng đưa Reviewer (mục 3 xong).
- Tính phút, làm tròn lên. Nghỉ giữa chừng thì trừ thời gian nghỉ.
- Không tính: cài đặt môi trường lần đầu, thời gian chờ trả lời câu hỏi (ca g10).

Agent cũng không tính thời gian chờ người (eval tự trả lời J1, tự đồng ý kế hoạch, tự duyệt). Vì vậy hai con
số đều là **thời gian làm**, không gồm thời gian Reviewer.

## 5. Chấm đúng/sai (bằng code, giống agent)

Sau khi dừng đồng hồ, chạy bộ chấm của golden lên bảng đích của DE:

```bash
python eval/baseline/check_de.py g01_three_sources --db path/to/dev.duckdb --table fct_daily_revenue
```

Lệnh in `Khớp` hoặc chỗ lệch. Ghi kết quả vào cột `ghi_chú` (ví dụ `khớp` hoặc `lệch: 1/2 dòng khác`).
Không sửa tiếp sau khi chấm; nếu sửa thì ghi thêm một dòng mới với tổng thời gian.

## 6. Ghi kết quả

Thêm một dòng vào `eval/baseline/human_baseline.csv`, mỗi ca một dòng:

| Cột | Ý nghĩa | Ví dụ |
|---|---|---|
| `case_id` | tên thư mục ca | `g01_three_sources` |
| `người_làm` | tên hoặc mã người làm | `de_a` |
| `kinh_nghiệm` | số năm làm DE | `3` |
| `phút` | thời gian theo mục 4 | `42` |
| `ghi_chú` | kết quả chấm mục 5 + điều đáng chú ý | `khớp; mất 10 phút với định dạng ngày` |
| `ngày` | ngày làm, `YYYY-MM-DD` | `2026-10-12` |

Ô để trống được hiểu là chưa đo. Sau đó chạy `python eval/run_eval.py --skip-tests` để cập nhật
`eval/results/report.md`.

## 7. Giới hạn cần ghi khi báo cáo

- Dữ liệu golden nhỏ và sạch hơn dữ liệu công ty: cả hai bên đều nhanh hơn thực tế.
- Một DE không đại diện cho mọi DE. Ghi kinh nghiệm và số người đo.
- Agent chạy trên một máy, một nhà cung cấp LLM; thời gian phụ thuộc mạng và model.
