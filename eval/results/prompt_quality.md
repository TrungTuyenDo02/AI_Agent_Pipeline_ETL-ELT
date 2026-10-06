# Chất lượng golden: prompt v1 so với prompt mới (U1 giai đoạn 2)

- Cũ: prompt v1 (tiếng Việt, JSON tả bằng lời), chạy 2026-10-02 • openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- Mới: codegen v2, optimizer v2, planner v5, testgen v2 (tiếng Anh, structured output, ngữ cảnh gọn) • openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- 12 ca golden, chấm bằng code (so expected.csv). Mỗi phiên bản chạy **một lần**: LLM có dao động, chênh 1 ca chưa đủ kết luận.
- Lưu ý: lần chạy cũ trước khi có bước duyệt kế hoạch J1b; eval tự đồng ý kế hoạch nên không đổi số lần gọi LLM.

| Chỉ số | v1 | Mới | Nhận xét |
|---|---:|---:|---|
| Kết quả đúng | 12 | 12 | giữ nguyên |
| Đạt ngay lần đầu (0 lỗi V1/V2) | 10 | 11 | tốt hơn |
| Chọn đúng ELT/ETL | 12 | 12 | giữ nguyên |
| Ca rõ mà vẫn hỏi (càng ít càng tốt) | 0 | 0 | giữ nguyên |
| Hỏi làm rõ ở ca mơ hồ (g10) | 1 | 1 | giữ nguyên |
| Tổng vòng sửa (lỗi V1/V2) | 2 | 1 | tốt hơn |
| Token trung bình mỗi ca | 8530 | 8666 | +1,6% |
| Chi phí trung bình mỗi ca (USD) | 0.005511 | 0.007027 | +27,5% |
| Thời gian trung bình (s) | 43.1 | 50.4 | +16,9% |
| Tỉ lệ token vào trúng cache | — (chưa ghi) | 30.7% |  |

## Từng ca

| Ca | v1: đúng / hỏi / lỗi V | Mới: đúng / hỏi / lỗi V | Chi tiết mới |
|---|---|---|---|
| g01_three_sources | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 3 dòng |
| g02_duplicate_rows | ✓ / 0 / 1 | ✓ / 0 / 0 | Khớp 2 dòng |
| g03_refunds | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 2 dòng |
| g04_mixed_dates | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 2 dòng |
| g05_vnd_format | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 2 dòng |
| g06_one_to_many_join | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 2 dòng |
| g07_null_amounts | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 2 dòng |
| g08_cross_source_keys | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 2 dòng |
| g09_customer_dimension | ✓ / 0 / 1 | ✓ / 0 / 1 | Khớp 3 dòng |
| g10_ambiguous_request | ✓ / 2 / 0 | ✓ / 2 / 0 | đã hỏi 2 câu làm rõ |
| g11_monthly_by_channel | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 3 dòng |
| g12_pii_etl | ✓ / 0 / 0 | ✓ / 0 / 0 | Khớp 2 dòng |
