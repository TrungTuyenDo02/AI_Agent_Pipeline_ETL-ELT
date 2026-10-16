# ADR 0013 — Đối chiếu lại bản tối ưu trên sandbox, lỗi thì khôi phục bản gốc

- Ngày: 2026-10-16 • Trạng thái: chấp nhận • Bổ sung cho [ADR 0003](0003-v-node-bang-code-va-testgen-mu-code.md)

## Vấn đề

V3 chỉ so bản tối ưu với bản gốc trên các bộ dữ liệu thử do E2 sinh. Sau khi áp dụng, V1 + V2 chạy lại nhưng V2 chỉ kiểm `dbt build`
và kiểu cột, nên nếu bước chuyển SQL về `ref()` hoặc dữ liệu thật làm lệch kết quả thì không ai phát hiện. Bản tối ưu lỗi ở V1/V2 lại
quay về Codegen (tốn token, LLM có thể sửa lệch nghiệp vụ) dù bản gốc đã qua V1 + V2, và lượt lỗi bị cộng vào bộ đếm sửa.

## Quyết định

- V3 áp dụng bản tối ưu thì giữ `opt_baseline` = code gốc + dấu vân tay bảng đích gốc trên `sandbox.duckdb` (cột + kiểu, số dòng,
  tổng băm từng dòng, số thực làm tròn theo `COMPARE_ABS_TOL`). Không chụp được thì không áp dụng.
- V2 chạy lại bản tối ưu phải ra đúng dấu vân tay đó. Đạt → ghi thêm dòng đối chiếu `sandbox` vào báo cáo tối ưu.
- V1/V2 không đạt khi đang thử → node mới `opt_revert` (V, code thuần, 0 token): trả code gốc, ghi `skipped` kèm lý do, chạy lại
  V1 + V2. Lỗi này không ghi sổ lỗi và không tính vào lượt sửa của Codegen.

## Hệ quả

- Thêm một lần `dbt build` khi áp dụng tối ưu (và một lần nữa nếu phải khôi phục); không thêm lời gọi LLM nào.
- State thêm trường `opt_baseline` (không bắt buộc): lần chạy cũ đang dừng không có trường này thì chạy như trước.
