---
paths:
  - "src/agents/tools/**/*.py"
  - "tests/test_verifiers.py"
  - "tests/test_optimizer.py"
---

# Quy tắc an toàn SQL

- Mọi SQL do LLM sinh phải được parse bằng sqlglot trước khi chạy.
- Chặn lệnh phá dữ liệu và tên bảng/cột không có trong schema.
- Chỉ chạy trong sandbox DuckDB. Không thêm đường chạy sang kho thật.
- Kết quả sau tối ưu phải so khớp hai chiều với bản gốc trên đủ 5 bộ dữ liệu thử.
