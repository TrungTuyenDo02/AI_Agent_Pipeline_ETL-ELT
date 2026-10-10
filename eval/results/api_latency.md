# Thời gian phản hồi API

> Sinh bởi `eval/api_latency.py` ngày 2026-10-10. 0 token. Mỗi endpoint đo 100 lần liên tiếp sau 3 lần chạy nóng.

**Điều kiện đo:** gọi thẳng ứng dụng FastAPI trong cùng tiến trình (không qua mạng), một client đã đăng nhập,
LLM `mock`, SQLite trong thư mục tạm (không phải PostgreSQL), Windows 10, Python 3.11.9. Đây là thời gian xử lý của ứng dụng, **chưa gồm độ trễ mạng**; chỉ chạy 1 lượt đo.

| Endpoint | p50 (ms) | p95 (ms) | Lớn nhất (ms) |
|---|---:|---:|---:|
| `GET /health` | 3.2 | 4.2 | 5.3 |
| `GET /api/v1/runs?limit=20` | 5.0 | 6.2 | 7.1 |
| `GET /api/v1/runs/{id} (đã xong tới bản duyệt)` | 11.4 | 15.3 | 17.5 |

Tái hiện: `python scripts/tasks.py api-latency`.
