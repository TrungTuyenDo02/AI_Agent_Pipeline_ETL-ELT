# ADR 0014 — Sổ chi phí LLM và giữ trước ngân sách cho từng lượt gọi

- Ngày: 2026-10-17 • Trạng thái: chấp nhận • Thay cách tính trần ngày (`check_limits` đọc `summary.cost_usd` của run)

## Vấn đề

Trần tiền chỉ được kiểm lúc nhận việc, dựa trên `cost_usd` trong `summary` của run, lọc theo ngày tạo run. Nhiều lượt gọi tốn tiền
không vào số này: lỗi bị cắt ở `max_tokens`/`refusal` của Anthropic và `LengthFinishReasonError` của OpenAI (ném lỗi trước khi ghi
usage), lượt chính thất bại trước khi chuyển dự phòng, nút "Hỏi AI" (drift_advice). Model chưa có giá được tính 0 USD. Job đang chạy
không giữ trước ngân sách nên hai job có thể cùng dùng phần còn lại; chưa có mức vượt tối đa được bảo đảm.

## Quyết định

- Mọi lượt gọi LLM thật đi qua `CostMeter` (`src/services/llm.py`) và sổ `src/services/cost_ledger.py`. Mock không đi qua.
  Bước V: code thuần, 0 token.
- Bảng `llm_calls`: mỗi lượt gọi một dòng (người, run, task, model, token, tiền, trạng thái). Chỉ metadata, không lưu prompt hay phản hồi.
  Bảng `budget_counters(scope, subject, day)`: số đang giữ và số đã tính cho từng hạn mức `run` / `user` (ngày) / `global` (ngày).
  Tiền lưu bằng micro-USD (số nguyên). Ngày theo giờ Việt Nam, lấy lúc giữ trước.
- **Trước khi gọi:** model chưa có giá thì dừng (`LLMConfigError`), kể cả model dự phòng. Dự toán xấu nhất =
  (số ký tự prompt + schema)/2 token vào, cộng `max_tokens_for(task)` token ra, nhân (1 + `SDK_MAX_RETRIES`). Giữ trước trên cả ba hạn
  mức trong một giao dịch bằng `UPDATE … WHERE spent + reserved + :x <= :limit` và kiểm `rowcount`. Luôn theo thứ tự run → user →
  global để hai giao dịch không khóa chéo nhau. Một hạn mức không đủ thì hủy cả giao dịch và báo "Không đủ ngân sách để giữ trước lượt
  gọi này" (`LLMBudgetError`): không gọi, không chuyển dự phòng. Bước giữ trước nằm trước circuit breaker nên bị từ chối thì không
  chiếm lượt thăm dò.
- **Dự phòng** giữ trước một khoản riêng lúc chuyển sang. Không giữ gộp từ đầu, để khi còn xa trần thì không bị chặn sớm.
- **Quyết toán đúng một lần** (`UPDATE … WHERE status = cũ`):
  - Có usage (kể cả lỗi bị cắt hay từ chối) thì ghi tiền thật. Token của lượt thất bại cũng cộng vào `RUN_TOKEN_BUDGET`.
  - Mã 400/401/403/404/422 (máy chủ từ chối ngay, SDK không gọi lại) thì `released`, hoàn khoản giữ trước.
  - Đang ngắt mạch, chắc chắn chưa gửi, thì cũng `released`.
  - Còn lại (timeout, mất kết nối, lỗi không rõ) thì `unknown`: khoản dự toán chuyển thành chi phí tạm, không tự hoàn.
- **Treo, chạy lại:** quá TTL (`timeout × (1 + retries) + 60 s`) thì chuyển `unknown`. Phản hồi về muộn vẫn quyết toán được từ
  `unknown`. Reviewer đối soát tay bằng `python -m src.cli cost --settle <mã> --usd <số> --as reviewer` (bước J).
- **Người, run:** runner gắn (người tạo run, run_id); API "Hỏi AI" gắn người bấm. Lượt gọi không có ngữ cảnh (eval, script) tính cho
  `system`: không áp trần người nhưng vẫn tính trần toàn hệ thống.
- Trần mới `RUN_COST_BUDGET_USD`, `LLM_GLOBAL_DAILY_BUDGET_USD` mặc định 0 (tắt) cho tới khi người vận hành chọn mức.
  `LLM_DAILY_BUDGET_USD` giữ nguyên ý nghĩa, nay đọc từ sổ.

## Hệ quả

- Hai bảng mới (migration `0008_llm_cost_ledger` cho Postgres; SQLite tự tạo). Mỗi lượt gọi thật thêm 2–3 câu SQL nhỏ.
- Dự toán bảo thủ: khi gần chạm trần, lượt gọi có thể bị chặn dù chi phí thật vẫn đủ. Thông báo nói rõ là "không đủ để giữ trước".
- Retry bên trong SDK không nhìn thấy được nên phải dự toán theo trường hợp xấu nhất. Lượt `unknown` tính bằng dự toán cho tới khi đối soát.
- Số USD là ước tính theo bảng giá nội bộ (`src/services/cost.py`), chưa đối soát với hóa đơn.
- Dự phòng phía máy chủ của Anthropic (`fallbacks="default"`) có thể trả lời bằng model khác với model đã dự toán:
  - Model đó có giá: quyết toán theo tiền thật, nên lượt đó có thể vượt trần một khoản nhỏ.
  - Model đó chưa có giá: ghi `unknown` và giữ nguyên khoản dự toán, không tính 0 USD.
- `summary.cost_usd` của run vẫn giữ để hiển thị; số này không gồm lượt thất bại, nên có thể nhỏ hơn số trong sổ.
