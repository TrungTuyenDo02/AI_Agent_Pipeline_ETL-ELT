# ADR 0012 — Bản vá nhanh khi nguồn đổi cấu trúc (patch fast-path)

- Ngày: 2026-10-16 • Trạng thái: chấp nhận • Bổ sung cho [ADR 0010](0010-giam-sat-thay-doi-cau-truc-nguon.md)

## Vấn đề (vì sao phải làm)

Khi chạy thử, người dùng bấm "Đề xuất bản vá" sau một thay đổi cấu trúc nguồn và thấy agent **hỏi lại từ đầu, lập kế hoạch lại**, dù những bước đó đã làm và đã được duyệt.
Nguyên nhân nằm ở thiết kế cũ (ADR 0010): bản vá là một run MỚI được dựng từ một đoạn văn (yêu cầu gốc + danh sách thay đổi) rồi đi lại cả luồng
`input_gate → drift_gate → planner → clarify → plan_review → … → codegen`. Ba hệ quả:

1. Người dùng bị hỏi lại điều đã trả lời (J1) và phải duyệt lại kế hoạch (J1b) dù nghiệp vụ không đổi, chỉ nguồn đổi.
2. Tốn token cho việc không cần LLM: đổi tên cột hay đổi kiểu là phép sửa cơ học, sinh lại cả pipeline là phí và còn có thể làm lệch code đã được duyệt.
3. Planner có thể lập kế hoạch khác lần trước (LLM không tất định), nên "bản vá" không còn là bản vá của pipeline cũ.

## Cách một DE kỳ cựu xử lý (nguyên tắc áp dụng)

- **Đặc tả đã duyệt là hợp đồng.** Nguồn đổi cấu trúc không làm nghiệp vụ đổi, nên không lập kế hoạch lại; làm *phân tích tác động* (impact analysis) rồi sửa đúng chỗ.
- **Lớp staging là lớp đệm** (anti-corruption layer). Cột nguồn đổi tên thì sửa MỘT dòng ở staging (`ordered_at AS order_date`); bảng đích không phải đổi.
  Cột nguồn đổi kiểu thì ép về kiểu cũ ở staging (`try_cast(col AS <kiểu cũ>)`); phần phía sau vẫn thấy kiểu cũ.
- **Sửa tất định trước, AI sau** (J-E-V của dự án). Phép sửa cơ học làm bằng code trên cây cú pháp, không dùng LLM. Chỉ phần *đổi nghĩa* (bỏ cột đang dùng) mới cần AI,
  và chỉ phần *chỉ người biết* (cột nào thay cột đã mất) mới hỏi người, bằng câu hỏi trắc nghiệm đúng một câu.
- **Bằng chứng tự động, không bằng mắt.** Sau khi sửa, chạy lại V1, V2 và **so bảng đích với lần chạy gốc**: đổi tên thuần phải ra kết quả y hệt.
  Khác thì không im lặng: đưa lên màn duyệt J2.
- **Cái gì tự sửa được thì nói trước.** Người xem "kế hoạch vá" (0 token) TRƯỚC khi tạo run: thay đổi nào tự sửa bằng code, nào cần AI, nào cần họ chọn, nào không vá được.

## Quyết định (làm gì trong code)

| Phần | File | Việc |
|---|---|---|
| Sửa SQL tất định | `src/agents/tools/drift_fix.py` | `rewrite(sql, bảng, bước)` bằng sqlglot: `rename` và `cast`. Không thay chuỗi: làm trên cây cú pháp, chỉ đổi cột thuộc ĐÚNG câu SELECT đọc bảng nguồn, giữ `config()`, `source()`, `ref()`. Cột nằm thẳng ở danh sách chọn được đặt bí danh bằng tên cũ. Jinja lạ hoặc lỗi cú pháp thì trả `None` (không đoán). |
| Kế hoạch vá | `src/services/patch_plan.py`, `src/models/drift.py` | `build_plan` phân loại từng thay đổi: `none` / `code` / `llm` / `ask` / `blocked`. Câu hỏi chỉ có tên cột và kiểu. `apply_plan` áp bản sửa; file không sửa an toàn được thì chuyển sang `llm` đúng file đó. `seed_state` mang đặc tả, câu trả lời J1, lựa chọn J1b và code của lần chạy gốc sang run vá. |
| Node của run vá | `src/agents/nodes/patch.py` | `patch_start` (chụp cấu trúc hiện tại cho J2 kiểm lại), `patch_apply` (áp bản sửa, bỏ test ép kiểu cũ để Testgen dựng lại theo hồ sơ mới, dựng lời nhắc cho Codegen nếu còn phần cần AI), `patch_verify` (so bảng đích với lần chạy gốc). Cả ba là code thuần, 0 token. |
| Graph | `src/agents/graph.py`, `routing.py` | Điểm vào rẽ nhánh: `patch_of` có giá trị thì `START → patch_start → ingest → profiler → patch_apply → testgen (codegen chỉ khi còn phần cần AI) → V1 → V2 → patch_verify → package → J2`. Bỏ G0, G1, E1, J1, V0, J1b, Vs, E4. Vòng sửa V1/V2 và cứu hộ giữ nguyên. |
| Codegen có giới hạn | `src/agents/nodes/codegen.py` | Run vá chỉ gửi các file cần AI sửa (và model liên quan qua `ref()`), không gửi cả bộ. Khi cần AI thì "đáp án" của test đối soát cũng viết lại (Testgen mù code). |
| API | `src/api/runs.py` | `POST /runs/{id}/patch-plan` (xem kế hoạch, không tạo run) và `POST /runs/{id}/patch` (kèm `answers`). Chưa trả lời đủ câu hỏi hoặc có thay đổi không vá được thì 409, không tạo run. |
| Khép vòng | `src/agents/nodes/review.py` | Reviewer duyệt run vá → các thay đổi đã vá thành `acknowledged` và cấu trúc mới thành bản chuẩn: số đỏ ở chuông giảm. |
| Giao diện | `frontend/components/drift/PatchPanel.tsx` | Bảng kế hoạch vá (nhãn Tự sửa bằng code / Cần AI / Cần bạn chọn / Không vá được), câu hỏi chọn cột, ước tính token. Ở run vá, đường ống tiến trình ghi các bước J1, J1b "dùng lại từ lần chạy gốc". |
| Gemini diễn giải | `src/services/drift_advice.py` | Giữ nguyên: nút "Hỏi AI diễn giải thêm" gọi Gemini flash-lite (`drift_advice` trong `config/models.yaml`), chỉ nhận tên bảng/cột/kiểu/đường dẫn file. |

## Kiến thức kỹ thuật dùng ở đây

- **Phân tích cú pháp thay cho thay chuỗi (AST rewriting):** thay chuỗi `order_date` → `ordered_at` sẽ đổi luôn bí danh đầu ra và tên cột ở CTE sau, làm hỏng bảng đích.
  Duyệt cây sqlglot cho biết cột thuộc câu SELECT nào, bảng nào (`find_ancestor`), và phân biệt cột ở danh sách chọn với cột trong biểu thức.
- **Bí danh giữ hợp đồng đầu ra (contract at the boundary):** staging công bố tên cột ổn định cho phần còn lại, nguồn đổi thì chỉ staging đổi.
- **Ép kiểu về kiểu cũ (`try_cast`):** đưa kiểu của nguồn về kiểu đã được đặc tả dựa vào; giá trị không ép được thành rỗng và bị test ép kiểu của giai đoạn 5 đếm (`CAST_FAIL_THRESHOLD`).
- **Idempotent (chạy lại không đổi):** cột đã được ép đúng kiểu sẵn thì không đổi file; ghi là "đã đúng sẵn" thay vì gọi AI vô ích.
- **Phân tích tác động (blast radius) và lineage:** file bị ảnh hưởng suy từ phân tích SQL (`source()` → staging → `ref()` → mart), không quét cả bộ code.
- **Kiểm chứng hồi quy (regression check):** bảng đích của bản vá so với bảng đích của lần chạy gốc (`ORDER BY ALL`, so từng dòng). Đây là bằng chứng đo được bằng code.
- **Người trong vòng lặp ở chỗ đúng:** hỏi một câu trắc nghiệm có đáp án suy từ cấu trúc, thay vì hỏi lại cả yêu cầu. Quyết định đổi nghĩa vẫn do người.
- **LangGraph:** điểm vào có điều kiện (`add_conditional_edges(START, …)`), trạng thái khởi đầu truyền qua `payload` của lần chạy đầu để checkpoint lưu được và chạy lại từ bước lỗi được.

## Đã đo (eval/run_patch.py, kết quả: [patch.md](../../eval/results/patch.md), [patch_llm.md](../../eval/results/patch_llm.md))

6 kịch bản nguồn đổi cấu trúc trên sandbox (pipeline gốc dựng bằng mock):

- **5/6 xong không cần AI, 0 token**, qua V1 và V2, **bảng đích giống hệt lần chạy gốc**: 3 kịch bản được sửa bằng code (đổi tên cột; đổi tên kèm đổi kiểu; kiểu số thực
  thành chuỗi), 1 kịch bản (chuỗi thành số) pipeline đã tự phòng thủ sẵn nhờ ép kiểu ở staging nên bản vá không đổi file nào, 1 kịch bản chỉ thêm cột vô hại (không cần sửa).
- **1/6 cần AI** (bỏ cột đang dùng). Chạy thật với `gpt-6-luna`: 2 lần gọi (Codegen + Testgen), **8.327 token, 0,0027 USD**, 69 giây, qua V1 và V2. Bảng đích **khác** lần chạy gốc
  (60 dòng): mất cột thì doanh thu nguồn đó không còn tính được, và hệ thống đưa đúng điều này lên màn duyệt thay vì im lặng.
- Cách cũ (run mới, lập kế hoạch lại): trung bình 6.918 token (≈ 0,0045 USD) mỗi run đầy đủ (LLM thật, đo ở golden), chưa kể các câu hỏi lại và lần duyệt kế hoạch.
  Nghĩa là: phần cần AI **không rẻ hơn** một run đầy đủ về token (8,3k so với 6,9k trung bình); lợi ích ở nhánh này là người dùng không bị hỏi lại, không duyệt lại kế hoạch,
  và code cũ đã duyệt không bị viết lại ngoài file cần sửa. Lợi ích lớn nằm ở nhánh code (token 0).

## Giới hạn đã biết

- Kịch bản và số đo là mô phỏng trên sandbox DuckDB với dữ liệu sinh từ seed 42; chưa đo trên nguồn production.
- Bản vá tạo run mới nên tính vào hạn mức run mỗi ngày của người dùng (`USER_DAILY_RUN_LIMIT`).
- Trạng thái khởi đầu của run vá được truyền trong bộ nhớ lúc xếp hàng: nếu máy chủ khởi động lại trước khi run bắt đầu thì run bị kẹt ở trạng thái "đang chạy", phải bấm tạo lại bản vá.
  Sau khi graph đã bắt đầu thì checkpoint giữ đủ trạng thái.
- Cột không nằm ở danh sách chọn mà dùng không có tiền tố trong câu SELECT nhiều bảng không đoán được thuộc bảng nào: bản vá bỏ qua và chuyển file đó cho AI.
- Kiểu `decimal` được ép về `DECIMAL(38,10)` (ảnh chụp cấu trúc chỉ lưu kiểu chuẩn hóa, không lưu độ chính xác gốc).
- Bản vá vẫn không tự chạy hay tự merge: chỉ người bấm "Tạo bản vá" mới tạo run, và run phải được Reviewer duyệt ở J2 (CLAUDE.md mục 0.6).
