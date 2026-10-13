# Chạy demo P-113 trên máy của bạn (không cần PostgreSQL, không cần khóa API)

Demo dùng **LLM mô phỏng** (câu trả lời cố định) và SQLite cho đăng nhập, nên không cần tài khoản hay khóa nào.

## Cần cài trước

- **Python 3.11** (kiểm tra: `python --version`)
- **Node.js 20.9 trở lên** (kiểm tra: `node --version`), tải ở <https://nodejs.org>

## Các bước (làm một lần)

Mở terminal trong thư mục đã giải nén:

```bash
python -m venv .venv
.venv\Scripts\activate            # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt   # mất vài phút
cd frontend
npm ci
cd ..
```

## Chạy

```bash
python demo/run_demo.py
```

Lần đầu mất 1–2 phút để dựng giao diện. Khi thấy khung "Mở trình duyệt", vào <http://localhost:3000>.

| Tài khoản | Vai trò | Mật khẩu |
|---|---|---|
| `an` | Engineer: tạo yêu cầu, trả lời, duyệt kế hoạch | `Demo-Engineer-2026` |
| `binh` | Reviewer: duyệt hoặc từ chối code | `Demo-Reviewer-2026` |
| `quantri` | Admin: quản lý tài khoản, xem nhật ký | `Demo-Admin-2026` |

Mật khẩu cố định này chỉ để demo trên máy cục bộ.

## Cách thử nhanh

1. Đăng nhập `an` → gõ yêu cầu: *Gộp dữ liệu đơn hàng 3 nguồn (Shopee CSV, Tiki JSON, website SQLite), tính doanh thu theo ngày* → **Gửi**.
2. Chọn đáp án các câu hỏi làm rõ → đọc kế hoạch → **Đồng ý**. Chờ các bước chạy xong.
3. Mở cửa sổ ẩn danh, đăng nhập `binh` → vào lần chạy → **Duyệt code** → xem bảng "Code đo | LLM nói" → **Duyệt**.

Kịch bản quay đầy đủ: [../docs/video-demo.md](../docs/video-demo.md).

## Lỗi hay gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `Chưa cài frontend` | Chạy `cd frontend && npm ci` |
| Cổng 3000 hoặc 8000 đang bị dùng | `DEMO_WEB_PORT=3010 DEMO_API_PORT=8010 python demo/run_demo.py` (Windows PowerShell: `$env:DEMO_WEB_PORT=3010; $env:DEMO_API_PORT=8010; python demo/run_demo.py`) |
| Muốn làm lại từ đầu | Dừng (Ctrl+C), xóa thư mục `demo_data/`, chạy lại |
| Trình xem code trống | Monaco tải từ internet (jsDelivr): cần có mạng |

Dừng demo: nhấn **Ctrl+C**.
