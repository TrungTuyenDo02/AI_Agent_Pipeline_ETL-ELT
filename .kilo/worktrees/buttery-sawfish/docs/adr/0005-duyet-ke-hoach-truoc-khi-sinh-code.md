# ADR 0005 — DE duyệt kế hoạch có giải thích trước khi agent sinh code (J1b)

- Ngày: 2026-10-03 • Trạng thái: chấp nhận

## Bối cảnh

Trước đây sau khi V0 đạt, agent đi thẳng tới sinh code; DE chỉ thấy đặc tả khi đã có bản duyệt J2. Nếu Planner hiểu
sai yêu cầu (chọn sai nguồn, sai mức gộp, sai cách tính) thì token sinh code, sinh test, chạy sandbox và tối ưu đều
lãng phí, và DE phải từ chối ở J2 rồi chờ thêm một vòng.

## Quyết định

- Thêm bước con người **J1b Duyệt kế hoạch** giữa V0 và E0: graph dừng (`interrupt`, kind `plan`).
- `PipelineSpec` thêm `plan_summary` (1–3 câu) và `plan` (các bước: `title`, `detail` làm gì với bảng/cột nào,
  `reason` vì sao). Planner (LLM) viết; nếu bỏ trống, code dựng kế hoạch tối thiểu từ đặc tả (`default_plan`).
- DE **Đồng ý** → agent chạy tiếp; **Yêu cầu sửa** (bắt buộc ghi chú) → ghi chú vào `plan_feedback`, Planner lập lại,
  V0 soát lại, J1b hỏi lại. Quá `MAX_REVIEW_ROUNDS` lần sửa → dừng.
- Kế hoạch là lời LLM (claimed) nên giao diện ghi rõ "LLM lập — bạn kiểm tra"; pass/fail vẫn do V-node đo.
- Kế hoạch đã duyệt được ghi vào `PULL_REQUEST.md` và hiện lại ở màn Tổng quan.

## Hệ quả

- Thêm một lần dừng chờ người (CLI hỏi approve/revise; web có nút; eval và `--auto-answer` tự đồng ý).
- Sai hiểu yêu cầu bị chặn trước khi tốn token sinh code.
- Sơ đồ Archify (`docs/architecture.*`) chưa có ô J1b — người dùng cập nhật; bản Mermaid đã thêm.
