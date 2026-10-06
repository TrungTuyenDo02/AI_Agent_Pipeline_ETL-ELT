# Evaluation Report — P-113

> Sinh tự động bởi `eval/run_eval.py` ngày 2026-10-02. Chỉ ghi số đã đo thật; chưa đo ghi `—`.
> Số chạy bằng `mock` KHÔNG phải chất lượng mô hình thật.

## 1. Chỉ số

| Chỉ số | Provider/model | Kết quả |
|---|---|---|
| pytest | mock (không cần khóa) | — đạt, 0 lỗi |
| Độ phủ code | — | — (ngưỡng 60%) |
| Mutation: bắt được lỗi giả | code (0 token) | 11/12 (91.7%) |
| Mutation: báo động nhầm ở đối chứng | code (0 token) | 0/1 |
| Golden: kết quả đúng khớp SQL chuẩn | code | 11/11 ca |
| Golden: agent đúng so với kết quả đúng | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 12/12 ca |
| Golden: đạt ngay lần đầu (0 lỗi V1/V2) | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 10/12 ca |
| Golden: chọn đúng mode ELT/ETL | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 12/12 ca |
| Golden: token / chi phí trung bình mỗi ca | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 8529 token / 0.0055 USD |
| Golden: thời gian trung bình yêu cầu → bản duyệt | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 43.1 s |
| ELT-Bench-Verified (10 task, 34 bảng): khớp bảng đúng | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 7/34 bảng |

Chi tiết: [mutation.md](mutation.md) • [golden_reference.md](golden_reference.md) • [golden_agent.md](golden_agent.md) • [eltbench_reference.md](eltbench_reference.md) • [eltbench_agent.md](eltbench_agent.md) • [tpch_benchmark.md](tpch_benchmark.md)

## 2. Thời gian phản hồi API

— (đo ở Phase 7 khi có đủ endpoint).

## 3. Phản hồi người dùng thử

— (chưa thu thập; cần 3–5 người).

## 4. Truy vết test → tính năng

| Test | Tính năng |
|---|---|
| `tests/test_verifiers/test_spec_check.py` | V0 Soát đặc tả: chặn khi còn điểm chưa rõ, grain sai, mode sai |
| `tests/test_verifiers/test_data_nodes.py` | E0 Nhận nguồn, P Soi dữ liệu (định dạng ngày/tiền), E2 Dữ liệu thử |
| `tests/test_verifiers/test_sql_tools.py` | V1: chặn lệnh nguy hiểm, đường dẫn ngoài sandbox, bảng/cột bịa |
| `tests/test_verifiers/test_safety_and_sandbox.py` | V1 An toàn + V2 Sandbox (dbt build thật, bắt SUM→AVG) |
| `tests/test_agents/test_llm_nodes.py` | E1 Planner, E3 Codegen, E3b Testgen mù code |
| `tests/test_agents/test_fix_loop.py` | Vòng sửa E3 ↔ V1/V2: lỗi gốc, gợi ý cột, biên dịch thử, chặn hỏi lặp |
| `tests/test_agents/test_routing.py` | Rẽ nhánh graph (vòng sửa ≤3, cứu hộ, giới hạn vòng) |
| `tests/test_agents/test_graph.py` | Graph end-to-end: J1 → J2, duyệt/từ chối, quyền, cứu hộ |
| `tests/test_optimizer/` | E4 Optimizer + V3 Đối chiếu (applied / skipped / loại vì lệch) |
| `tests/test_services/test_llm.py` | Cổng LLM: mock/openai/google, model theo bước, dự phòng Gemini |
| `tests/test_services/test_store_and_memory.py` | Kho lần chạy + sổ lỗi cần duyệt |
| `tests/test_cli/test_cli.py` | CLI: doctor, seed, run, review, errors, optimize |
| `tests/test_api/test_routes.py` | API: /health, danh sách lần chạy |
| `tests/test_eval/` | Bộ chấm ELT-Bench, golden (khớp SQL chuẩn), đột biến áp dụng được |
