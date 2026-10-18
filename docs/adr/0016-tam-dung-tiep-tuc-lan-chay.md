# ADR 0016 — Tạm dừng / tiếp tục lần chạy ở ranh giới giữa hai node

- Ngày: 2026-10-18 • Trạng thái: đề xuất, chờ chủ dự án duyệt thay đổi hợp đồng (mục "Hợp đồng") • Không đổi tên node, không nới
  hàng rào kiểm chứng

## Vấn đề

Engineer tạo yêu cầu rồi nhận ra yêu cầu sai, hoặc muốn ngừng tốn chi phí AI trong lúc xem lại, nhưng không muốn mất phần đã chạy.
Trước đây chỉ có các điểm dừng chờ người (J1, J1b, G1, Vs, cứu hộ, J2) và "chạy lại từ bước lỗi". Không có cách dừng một lần chạy
đang chạy hay đang xếp hàng mà vẫn tiếp tục được sau đó.

## Quyết định

- **Ranh giới node.** Runner chạy graph từng node một: `graph.stream(..., interrupt_before="*")`. LangGraph lưu checkpoint rồi dừng
  trước node kế tiếp. Giữa hai node, runner gọi `store.take_pause(run_id)`; có yêu cầu thì trả `StepResult(paused=True)` và trả lại
  luồng nền. Node đang chạy luôn được chạy xong, kể cả lời gọi LLM hoặc `dbt build` đã gửi. Không ngắt giữa chừng, nên không có
  checkpoint nửa vời. Trần số bước mỗi lượt (`RECURSION_LIMIT` = 200) do runner đếm, thay `recursion_limit` của LangGraph.
- **Yêu cầu bền vững.** Bảng `run_controls` (migration `0010_run_controls`; SQLite do `Store` tự tạo) có tối đa một dòng mỗi lần chạy.
  `request_pause` chỉ ghi khi `runs.status = 'running'`; bấm lặp không thêm dòng. `update_run` sang trạng thái khác `running` xóa
  dòng trong cùng giao dịch, nên lần chạy tự xong, lỗi hoặc tới bước chờ người không bị ghi đè thành "đã tạm dừng".
- **Xếp hàng.** Yêu cầu tạm dừng đến khi lần chạy còn trong hàng đợi được nhận ngay ở ranh giới đầu tiên, trước mọi node. Không chạy
  G0, Planner hay gọi LLM nào. Lần chạy thường chưa có checkpoint: tiếp tục dựng lại đầu vào ban đầu từ bản ghi (`request_text`,
  `requester`).
- **Run vá.** Đầu vào của run vá (`patch_of`, spec, câu trả lời, code gốc) không dựng lại được từ bản ghi. `propose_patch` gọi
  `runner.prepare_patch` NGAY khi tạo, trước khi xếp hàng: chỉ chạy bước nhận đầu vào và định tuyến START (code, 0 token), lưu
  checkpoint rồi dừng trước `patch_start`. Tạm dừng khi còn xếp hàng, hay server tắt trước khi job chạy, vẫn giữ đầu vào; tiếp tục
  hoặc chạy lại đi thẳng `patch_start`, không qua G0, Planner, J1, J1b. Không lưu được đầu vào thì run vá thành `failed` và API
  trả 500 kèm lời nhắc, chưa xếp hàng.
- **Tiếp tục.** `continue_run` chạy tiếp từ checkpoint cuối, cùng `run_id`. Node đã xong không chạy lại, không gọi lại AI; các bước
  chờ người phía sau vẫn đi đúng như cũ. Câu trả lời `Command(resume=…)` luôn được ghi vào graph trước khi kiểm cờ tạm dừng.
- **Quyền.** Chỉ Engineer là người tạo yêu cầu (`record.requester`) được tạm dừng hoặc tiếp tục. Reviewer, Admin và Engineer khác
  bị chặn ở backend (403/404), độc lập với web. Giữ CSRF (`X-Requested-With`). Chế độ khách (ADR 0015) không có nút này.
- **Hạn mức.** Tiếp tục kiểm như lượt chạy mới: số lần chạy cùng lúc và trần chi phí người dùng hôm nay (429, `jobs.check_limits`).
  Việc kiểm này chạy TRONG khóa của hàng đợi, cùng lúc với nhận vào hàng (`JobQueue.submit(..., limits=True)`). Hai lần chạy khác
  nhau của một người bấm Tiếp tục đồng thời không cùng lọt giới hạn. Trong khóa chỉ đọc DB, không gọi lại hàng đợi, nên không kẹt.
  Thêm trần riêng của lần chạy: token đã ghi trong checkpoint (`RUN_TOKEN_BUDGET`), USD theo sổ chi phí (`RUN_COST_BUDGET_USD`) và
  ngân sách toàn hệ thống hôm nay (409). Bị từ chối thì trạng thái `paused` giữ nguyên.
- **Chống chạy trùng.** `JobQueue.submit` kiểm "đang bận" và đưa vào hàng trong cùng khóa. Lần bấm thứ hai nhận `RunBusyError` →
  409. Lượt tiếp tục chạy `guard` trong khóa để hai yêu cầu đồng thời chỉ một yêu cầu được nhận. Thay đổi này cũng áp cho trả lời
  J1/J1b/J2, cứu hộ và chạy lại. Trước đây bấm hai lần đưa lần chạy vào hàng hai lượt; lượt thứ hai bị bỏ trong luồng nền
  (`RunStateError`) nhưng API vẫn trả 202.
- **Khởi động lại.** `fail_interrupted_runs`: lần chạy `running` có yêu cầu tạm dừng thành `paused`, kèm `summary.notice`, không đánh
  lỗi; tiếp tục thì làm lại đúng node đang dở lúc server tắt. Lần chạy đã `paused` giữ nguyên. Lần chạy `running` không có yêu cầu
  vẫn thành `failed` như cũ.
- **Kiểm toán.** `run.pause` khi nhận yêu cầu, `run.paused` khi thật sự dừng (`detail.next` = tên node kế tiếp, không có dữ liệu),
  `run.resume` khi được nhận vào hàng. Yêu cầu bị chặn không ghi `run.resume`.
- **J-E-V.** Đây là điều khiển vận hành, không thêm bước J/E/V. Mọi kiểm tra bằng code, 0 token.

## Hợp đồng (cần chủ dự án duyệt)

- `RunStatus.PAUSED = "paused"`: giá trị enum mới. Client cũ gặp giá trị lạ chỉ khi có lần chạy bị tạm dừng.
- `RunRecord.pause_requested: bool = False`: trường mới có mặc định. Checkpoint và bản ghi cũ đọc được; JSON cũ thiếu trường vẫn
  hợp lệ. Giá trị tính bằng `LEFT JOIN run_controls` và chỉ đúng khi `status = 'running'`.
- API mới: `POST /runs/{id}/pause` (202 `pausing`/`paused`, 403, 404, 409) và `POST /runs/{id}/resume` (202, 403, 404, 409, 429).
  `Accepted.status` có thêm giá trị `pausing`/`paused`, kiểu vẫn là chuỗi.
- Thay đổi hành vi: hành động đưa lần chạy vào hàng khi nó đang chạy hoặc đang xếp hàng nay trả 409. Trước đây có thể bị nhận trùng.

## Hệ quả

- Mỗi node thêm một lần đọc `get_state` và một câu `DELETE` nhỏ. Không đáng kể so với lời gọi LLM hoặc `dbt build`.
- Tạm dừng không tiết kiệm chi phí của node đang chạy. Web và API đều ghi rõ "Bước này vẫn có thể phát sinh chi phí AI".
- Các hành động khác (tạo yêu cầu, trả lời J1/J2, chạy lại, tạo run vá) vẫn kiểm hạn mức trước khi nhận vào hàng, ngoài khóa, như
  trước ADR này. Hai yêu cầu đồng thời của cùng người vẫn có thể cùng lọt giới hạn. Nằm ngoài phạm vi tạm dừng/tiếp tục; để lại
  làm việc sau.
- Run vá tạm dừng khi xếp hàng bằng code trước bản sửa này (commit `16fd218`) không có checkpoint đầu vào. Không khôi phục được;
  tạo lại bản vá. Bản ghi này chỉ có trên máy thử của snapshot WIP.
- Tiến trình từng bước (`events`) vẫn giữ trong bộ nhớ như trước, nên mất khi khởi động lại. Trạng thái, checkpoint và yêu cầu tạm
  dừng thì không mất.
