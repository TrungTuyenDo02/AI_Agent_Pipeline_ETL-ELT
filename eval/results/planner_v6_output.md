# Planner v6 — giảm token đầu ra (golden 12 ca, LLM thật)

- Ngày đo: 2026-10-08 • provider/model: openai / planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra
- Biến thay đổi DUY NHẤT: prompt `src/prompts/planner.md` v5 → v6 (quy tắc 13: kế hoạch 3–5 bước ngắn, giới hạn số từ cho
  `detail`/`reason`, tối đa 5 giả định). Cùng 12 ca golden, cùng bộ chấm, mỗi bản chạy **1 lần** (n=12 ca/bản).
- Mốc v5: `golden_agent_planner_v5.json` (2026-10-05). Bản v6: `golden_agent.json`.
- Token theo node lấy từ `llm_usage` của 12 lần chạy mỗi bản (checkpoint); token phần chữ đếm bằng tiktoken o200k_base.

| Chỉ số | v5 | v6 |
|---|---|---|
| Đúng (khớp expected.csv) | 12/12 | 12/12 |
| Ca có hỏi làm rõ | 1 (g10, đúng ý đồ) | 1 (g10) |
| Lỗi V1/V2 phải sửa | 1 | 0 |
| Planner: số lượt gọi | 15 | 13 |
| **Planner: token đầu ra / lượt** | **1.155** | **825 (−29%)** |
| Planner: chi phí | 0,0248 USD | 0,0164 USD |
| Phần `plan` trong spec (trung vị) | 338 token | 210 token (−38%) |
| Phần `assumptions` (trung vị) | 174 token | 86 token (−51%) |
| Số bước kế hoạch (trung vị / tối đa) | 5 / 5 | 5 / 5 |
| Tổng token đầu ra 12 ca | 40.530 | 31.727 (−22%) |
| Tổng chi phí 12 ca | 0,0843 USD | 0,0540 USD |
| Thời gian trung bình / ca | 50,4 s | 46,4 s |

Lưu ý khi đọc:
- Mỗi bản chỉ chạy 1 lần: **chưa đủ kết luận** về chi phí tổng. Một phần chênh tổng chi phí đến từ optimizer
  (v5 gọi 3 lần = 0,0256 USD, v6 gọi 1 lần = 0,0063 USD) — phụ thuộc SQL sinh ra, không do prompt Planner.
- Chỉ số gắn trực tiếp với thay đổi: token đầu ra mỗi lượt Planner và độ dài `plan`/`assumptions`.
- Độ đúng không giảm (12/12). Testgen/codegen dao động giữa hai lần chạy (testgen 575 → 692 token/lượt).
