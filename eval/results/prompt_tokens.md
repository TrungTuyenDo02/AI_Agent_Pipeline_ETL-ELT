# Token của prompt theo node (đo offline)

- Đếm bằng tiktoken `o200k_base`; số gần đúng, chưa gồm vài token khung tin nhắn của API.
- Phần tĩnh = system prompt + JSON Schema đầu ra gửi kèm (nếu bật structured output; ước tính bằng
  JSON gọn của schema, API có thể đóng gói khác một chút). Phần động = dữ liệu của lần chạy.
- OpenAI chỉ cache khi phần đầu giống hệt ≥ 1024 token: cột `cache?` cho biết phần tĩnh có đủ dài.
- 3 ca golden (g01 gộp 3 nguồn, g06 nối một-nhiều, g09 bảng chiều). Spec/code trong fixture là đầu ra
  thật của gpt-5.6-luna ngày 2026-10-02; `codegen_retry` chỉ có ở ca có lỗi thật (g09).
- Chỉ đo token ĐẦU VÀO. Token đầu ra và chất lượng (đúng/sai, pass lần đầu, số vòng sửa) cần khóa LLM:
  — (chưa đo, U1 giai đoạn 2).

## Trước / sau (trung bình các ca)

| Node | Tĩnh trước | Tĩnh sau | Δ tĩnh | Động trước | Động sau | Δ động | Tổng trước | Tổng sau | Δ tổng |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| planner | 1.310 | 1.163 | -11,2% | 673 | 377 | -44,0% | 1.983 | 1.540 | -22,4% |
| codegen | 794 | 607 | -23,6% | 1.764 | 971 | -45,0% | 2.558 | 1.578 | -38,3% |
| codegen_retry | 794 | 607 | -23,6% | 1.942 | 1.083 | -44,2% | 2.736 | 1.690 | -38,2% |
| testgen | 675 | 428 | -36,6% | 1.726 | 935 | -45,9% | 2.401 | 1.363 | -43,3% |
| optimizer | 317 | 295 | -6,9% | 1.166 | 497 | -57,4% | 1.483 | 792 | -46,6% |

## Chi tiết `before` (2026-10-05, prompt codegen=1, optimizer=1, planner=1, testgen=1 (bản trước khi có dòng version))

| Ca | Node | Tĩnh | Động | Tổng | cache? |
|---|---|---:|---:|---:|---|
| g01_three_sources | planner | 1.310 | 880 | 2.190 | có |
| g01_three_sources | codegen | 794 | 2.215 | 3.009 | không |
| g01_three_sources | testgen | 675 | 2.177 | 2.852 | không |
| g01_three_sources | optimizer | 317 | 1.232 | 1.549 | không |
| g06_one_to_many_join | planner | 1.310 | 608 | 1.918 | có |
| g06_one_to_many_join | codegen | 794 | 1.694 | 2.488 | không |
| g06_one_to_many_join | testgen | 675 | 1.656 | 2.331 | không |
| g06_one_to_many_join | optimizer | 317 | 1.149 | 1.466 | không |
| g09_customer_dimension | planner | 1.310 | 532 | 1.842 | có |
| g09_customer_dimension | codegen | 794 | 1.384 | 2.178 | không |
| g09_customer_dimension | codegen_retry | 794 | 1.942 | 2.736 | không |
| g09_customer_dimension | testgen | 675 | 1.346 | 2.021 | không |
| g09_customer_dimension | optimizer | 317 | 1.116 | 1.433 | không |

## Chi tiết `after` (2026-10-05, prompt codegen=2, optimizer=2, planner=5, testgen=2)

| Ca | Node | Tĩnh | Động | Tổng | cache? |
|---|---|---:|---:|---:|---|
| g01_three_sources | planner | 1.163 | 485 | 1.648 | có |
| g01_three_sources | codegen | 607 | 1.231 | 1.838 | không |
| g01_three_sources | testgen | 428 | 1.195 | 1.623 | không |
| g01_three_sources | optimizer | 295 | 449 | 744 | không |
| g06_one_to_many_join | planner | 1.163 | 345 | 1.508 | có |
| g06_one_to_many_join | codegen | 607 | 936 | 1.543 | không |
| g06_one_to_many_join | testgen | 428 | 900 | 1.328 | không |
| g06_one_to_many_join | optimizer | 295 | 482 | 777 | không |
| g09_customer_dimension | planner | 1.163 | 301 | 1.464 | có |
| g09_customer_dimension | codegen | 607 | 745 | 1.352 | không |
| g09_customer_dimension | codegen_retry | 607 | 1.083 | 1.690 | không |
| g09_customer_dimension | testgen | 428 | 709 | 1.137 | không |
| g09_customer_dimension | optimizer | 295 | 559 | 854 | không |

## Token đầu vào thật của OpenAI ở lần chạy gốc (prompt bản cũ hơn, chỉ để đối chiếu cách đếm)

| Ca | Lần gọi (task: input/output) |
|---|---|
| g01_three_sources | planner: 1870/1104, codegen: 2901/1442, testgen: 2744/476 |
| g06_one_to_many_join | planner: 1582/992, codegen: 2364/1638, testgen: 2207/841 |
| g09_customer_dimension | planner: 1506/853, codegen: 2071/1048, testgen: 1914/527, codegen: 2820/779, optimizer: 1440/295 |
