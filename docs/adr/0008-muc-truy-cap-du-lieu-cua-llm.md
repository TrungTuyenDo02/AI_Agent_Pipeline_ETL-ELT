# ADR 0008 — Mức truy cập dữ liệu của LLM và cửa duy nhất `build_llm_context`

- Ngày: 2026-10-15 • Trạng thái: chấp nhận • Điều chỉnh quyết định "LLM chỉ thấy schema" (CLAUDE.md 2.3, 2026-10-13)

## Bối cảnh

Chỉ cho LLM xem cấu trúc bảng là quá chặt: Planner cần biết dữ liệu bẩn kiểu gì (khóa trùng, ngày lẫn định dạng, tiền
`1.075.000`, rỗng nhiều) mới sinh đúng phép làm sạch. CLAUDE.md bản 2 mục 3.3 đề xuất ba mức truy cập theo từng nguồn.

## Quyết định

- Ba mức theo nguồn: `schema_only` < `profile` (mặc định `LLM_ACCESS_DEFAULT=profile`) < `masked_sample`. `profile` cho thấy số
  dòng, % rỗng, số giá trị khác nhau, tỷ lệ trùng khóa, **dạng giá trị** (chữ số → `9`, chữ cái → `a`) và phân bố các dạng;
  không có giá trị thật. Muốn quay về như cũ: `LLM_ACCESS_DEFAULT=schema_only` (cho nguồn đăng ký mới) hoặc `PATCH /sources/{id}`.
- Trần theo độ nhạy cảm: `high` → `schema_only`; `medium` → tối đa `profile`; `low` → tối đa `masked_sample`. Kiểm hai lần: khi đăng
  ký (API từ chối cấu hình sai) và trong `build_llm_context` (hạ mức + ghi nhật ký). Bảng không có thông tin mức (danh mục không
  đến từ sổ nguồn) coi là `schema_only`.
- Cột nhạy cảm (tên gợi ý thông tin cá nhân, admin đánh dấu, hoặc giá trị dạng email/điện thoại): chỉ số đếm và dạng giá trị, không
  min/max, không giá trị phổ biến. Danh sách giá trị phổ biến chỉ cho cột phân loại ≤ 10 giá trị (lặp ≥ 3 lần, không phải mã/tiền/
  ngày) của nguồn `low`.
- `src/services/llm_context.py` là cửa duy nhất tạo ngữ cảnh dữ liệu cho prompt (Planner, Codegen, Testgen, Optimizer). Bước "Soi dữ
  liệu" (P) vẫn tính hồ sơ trong sandbox nhưng chỉ đi vào prompt qua `LLMContext.build_profile`; `compact_catalog`/`compact_profile`
  thành hàm nội bộ. Test quét mã nguồn và quét mọi prompt của một lần chạy thử.
- Thông báo lỗi vào prompt phải qua `prompt_error` → `scrub_error` (`src/agents/tools/scrub.py`), thay `mask_literals` (giữ dạng giá
  trị) bằng `<đã che>` theo CLAUDE.md 3.4; sổ lỗi cũng chỉ lưu bản đã che.
- Giữ dữ liệu thật ra khỏi state/checkpoint: danh mục nguồn trong state không còn dòng mẫu (`sample`) và hồ sơ P không còn
  `examples`. **Còn lại (giới hạn đã biết):** `categories` của cột phân loại (đã che PII) vẫn nằm trong hồ sơ P để bước Vs so cấu
  trúc nguồn giữa các lần duyệt, và `sandbox.sample` (vài dòng bảng kết quả, đã che PII) vẫn nằm trong state để màn duyệt hiển thị
  cho người có quyền.

## Hệ quả

- Độ đúng của agent theo từng mức **chưa đo bằng LLM thật** (người dùng chọn chỉ dùng mock); `eval/results/llm_access.md` ghi số
  token từng mức, kiểm rò rỉ, và lệnh đo.
- Prompt Planner v9 (+1 câu về `stats.formats`); ngân sách token tĩnh nâng 1.290 → 1.360 (đo 1.316).
