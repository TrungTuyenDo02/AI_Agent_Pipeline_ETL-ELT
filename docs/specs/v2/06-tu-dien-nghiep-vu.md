> Đọc `docs/specs/v2/00-chung.md` (quy tắc chung) trước khi làm giai đoạn này.

## 6. Giai đoạn 6 — Từ điển nghiệp vụ (business glossary)

**Mục tiêu:** giúp planner đoán đúng bảng/cột và tăng độ chính xác cho tầng 1 của cửa kiểm tra.

- Mô hình `GlossaryTerm`: `term`, `synonyms`, `definition`, `maps_to` (bảng/cột hoặc biểu thức), `department_id` (rỗng = dùng chung). Chỉ `admin` được thêm/sửa; **agent chỉ đọc, không tự ghi**.
- Seed sẵn khoảng 15–20 thuật ngữ cho `P113 Retail` (doanh thu, đơn hàng, khách hàng, hoàn tiền, trùng đơn...), mỗi thuật ngữ có định nghĩa ngắn rõ ràng.
- Tầng 1 của cửa kiểm tra dùng thêm `term` + `synonyms` làm từ khóa nhận diện.
- Planner nhận **các thuật ngữ liên quan tới yêu cầu** (chọn bằng khớp từ khóa, tối đa N mục để không phình prompt), kèm định nghĩa, và phải nêu trong kế hoạch (J1b) thuật ngữ nào đã dùng. Thuật ngữ đi qua `build_llm_context` như mọi ngữ cảnh khác.
- API `GET/POST/PATCH /api/v1/glossary` (ghi chỉ `admin`) và một tab trong trang "Nguồn dữ liệu".
- **Nghiệm thu:** thêm ít nhất 5 ca vào bộ golden có dùng thuật ngữ nghiệp vụ; so sánh độ đúng trước/sau (LLM thật), ghi vào `eval/results/glossary.md`; số token prompt của planner tăng không quá 15%.
