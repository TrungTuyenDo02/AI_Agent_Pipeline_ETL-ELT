# Evaluation Report — P-113

> Sinh tự động bởi `eval/run_eval.py` ngày 2026-10-05. Chỉ ghi số đã đo thật; chưa đo ghi `—`.
> Số chạy bằng `mock` KHÔNG phải chất lượng mô hình thật.

## 1. Chỉ số

| Chỉ số | Provider/model | Kết quả |
|---|---|---|
| pytest | mock (không cần khóa) | 527 đạt, 0 lỗi |
| Độ phủ code | — | 92.18% (ngưỡng 60%) |
| Mutation: bắt được lỗi giả | code (0 token) | 11/12 (91.7%) |
| Mutation: báo động nhầm ở đối chứng | code (0 token) | 0/1 |
| Golden: kết quả đúng khớp SQL chuẩn | code | 11/11 ca |
| Golden: agent đúng so với kết quả đúng | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 12/12 ca |
| Golden: đạt ngay lần đầu (0 lỗi V1/V2) | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 11/12 ca |
| Golden: chọn đúng mode ELT/ETL | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 12/12 ca |
| Golden: token / chi phí trung bình mỗi ca | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 8665 token / 0.007 USD |
| Golden: thời gian trung bình yêu cầu → bản duyệt | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 50.4 s |
| Golden: tỉ lệ token đầu vào trúng cache | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 30.7% |
| ELT-Bench-Verified (10 task, 34 bảng): khớp bảng đúng | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | 7/34 bảng |
| Thời gian agent / DE làm tay (tổng các ca có cả hai) | openai/planner=gpt-5.6-luna, codegen=gpt-5.6-luna, testgen=gpt-5.6-luna, optimizer=gpt-5.6-terra | — (chưa có DE làm tay) |

Chi tiết: [mutation.md](mutation.md) • [golden_reference.md](golden_reference.md) • [golden_agent.md](golden_agent.md) • [eltbench_reference.md](eltbench_reference.md) • [eltbench_agent.md](eltbench_agent.md) • [tpch_benchmark.md](tpch_benchmark.md) • [prompt_tokens.md](prompt_tokens.md) • [verifier_report.md](verifier_report.md)

## 2. Agent so với DE làm tay

> Quy trình đo: [eval/baseline/PROTOCOL.md](../baseline/PROTOCOL.md). Số DE lấy từ `eval/baseline/human_baseline.csv`; ô trống ghi `—`. Thời gian agent lấy từ golden (tự trả lời J1, tự duyệt), không gồm thời gian người chờ. Agent / DE < 1 nghĩa là agent nhanh hơn.

| Ca | Agent (phút) | DE làm tay (phút, trung vị) | Số DE | Kinh nghiệm (năm) | Agent / DE |
|---|---:|---:|---:|---:|---:|
| g01_three_sources | 0,9 | — | — | — | — |
| g02_duplicate_rows | 1,0 | — | — | — | — |
| g03_refunds | 0,7 | — | — | — | — |
| g04_mixed_dates | 0,7 | — | — | — | — |
| g05_vnd_format | 0,6 | — | — | — | — |
| g06_one_to_many_join | 0,8 | — | — | — | — |
| g07_null_amounts | 0,6 | — | — | — | — |
| g08_cross_source_keys | 1,2 | — | — | — | — |
| g09_customer_dimension | 1,3 | — | — | — | — |
| g10_ambiguous_request | 1,2 | — | — | — | — |
| g11_monthly_by_channel | 0,6 | — | — | — | — |
| g12_pii_etl | 0,5 | — | — | — | — |

## 3. Công Reviewer

> Chỉ tính quyết định J2 của người thật (bỏ tài khoản `*-auto-reviewer` của eval). Số dòng đổi: so bản bị từ chối gần nhất với bản cuối; DE sửa tay sau khi tải zip không đo được. Kho hiện chỉ có lượt duyệt thử của nhóm khi phát triển (xem tên và ngày), chưa phải Reviewer độc lập: chưa đủ để kết luận.

| Chỉ số | Kết quả |
|---|---|
| Công Reviewer: duyệt ngay vòng đầu | 100% (5 lần chạy có người duyệt thật; người duyệt và ngày: binh 2026-10-02, bob 2026-10-02, de 2026-10-02) |
| Công Reviewer: số dòng code đổi sau khi từ chối | — |

## 4. Thời gian phản hồi API

— (đo ở Phase 7 khi có đủ endpoint).

## 5. Phản hồi người dùng thử

— (chưa thu thập; cần 3–5 người).

## 6. Truy vết test → tính năng

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
| `tests/test_verifiers/test_v1_redteam.py` | V1 red team (eval/verifier_bench): mọi ca tấn công bị chặn, mọi ca hợp lệ được qua |
| `tests/test_prompts/` | Chuẩn prompt: ngân sách token phần tĩnh, schema strict, ngữ cảnh gọn, ghi nhận cache |
| `tests/test_eval/test_baseline.py` | Mốc DE làm tay: đọc human_baseline.csv, so với agent, công Reviewer |
| `tests/test_agents/test_stages.py` | Web: trạng thái đường ống E/V/J, chi phí theo node + tỉ lệ trúng cache |
