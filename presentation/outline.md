# Dàn ý slide (10 slide, theo [README.md](README.md))

> Đây là **dàn ý nội dung**, chưa phải file `.pptx`. Có thể dựng nhanh trên PowerPoint/Google Slides/Canva; nếu cần file `.pptx` sinh sẵn, hãy yêu cầu riêng.
> Số liệu lấy từ [../eval/results/report.md](../eval/results/report.md); mỗi số phải đọc kèm điều kiện đo (chế độ mô phỏng hay LLM thật, ngày đo).

| # | Slide | Nội dung chính (tối đa 3 gạch đầu dòng mỗi slide) | Hình |
|---|---|---|---|
| 1 | Tiêu đề | **P-113 — Agent viết và tối ưu pipeline ELT/ETL**; *người phán đoán, agent thực thi, code kiểm chứng*; tên nhóm | Logo `frontend/public/brand/logo.svg` |
| 2 | Vấn đề | DE mất nhiều giờ viết lại staging, mart, test, DAG; dữ liệu bẩn (đơn trùng, ngày lẫn định dạng, tiền `1.075.000`); query chậm ít ai tối ưu | Ảnh dữ liệu bẩn minh họa |
| 3 | Giải pháp | Nói yêu cầu bằng lời → agent hỏi lại → trình kế hoạch → sinh dbt + DAG → chạy thử → tối ưu → Reviewer duyệt | Sơ đồ J-E-V rút gọn |
| 4 | Demo | Video 60 giây hoặc 3 ảnh: duyệt kế hoạch, bằng chứng "Code đo \| LLM nói", tối ưu trước/sau | `docs/screenshots/web_plan_review.png`, `web_review.png`, `web_optimize.png` |
| 5 | Kiến trúc | 17 bước: tròn = agent, vuông = code kiểm chứng (0 token), thoi = con người; vòng sửa tối đa 3 lần rồi cứu hộ | `docs/adr/architecture.png` |
| 6 | Công nghệ | LangGraph, FastAPI, dbt + DuckDB, sqlglot, Next.js 16, PostgreSQL + Alembic, Docker, GitHub Actions | Bảng Tech Stack |
| 7 | Kết quả (Traction) | Golden 12 ca: 12/12 đúng (LLM thật); mutation: bắt 11/12 lỗi giả; TPC-H: 11/13 query chậm được tối ưu, 10/11 không tốn token; **chưa có người dùng thật, chưa có DE làm tay** | Bảng từ `report.md` |
| 8 | Thị trường | Đội dữ liệu cỡ vừa chưa có công cụ sinh pipeline *có bằng chứng*. *Cần số liệu thị trường có nguồn: để trống nếu chưa có, không bịa* | — |
| 9 | Đội ngũ | TrungTuyenDo02 — toàn bộ hệ thống | Ảnh đội |
| 10 | Cần gì tiếp theo (Ask) | 3–5 DE làm tay theo `eval/baseline/PROTOCOL.md` để so sánh thời gian; thử trên dữ liệu thật của một đội; chuyển lưu trữ lần chạy sang PostgreSQL để deploy bền | — |

## Lời khuyên trình bày

- Mở bằng một câu chuyện ngắn: "Một yêu cầu gộp 3 nguồn đơn hàng" thay vì liệt kê công nghệ.
- Slide 7: nói cả **hạn chế** (1 lần chạy mỗi phép đo, nhãn kiểm thử do tác giả tự gán, dữ liệu là kho giả lập). Trung thực làm tăng độ tin cậy.
- Thời lượng gợi ý: 5 phút trình bày + 3 phút hỏi đáp; mỗi slide ≤ 30 giây, slide 4 và 7 được lâu hơn.
