"""Chạy demo cục bộ MỘT LỆNH, không cần PostgreSQL, không cần khóa API (LLM mô phỏng).

    python demo/run_demo.py

Việc script làm: đặt biến môi trường cho chế độ demo (đăng nhập bằng SQLite, LLM `mock`), tạo bảng bằng Alembic,
tạo 3 tài khoản mẫu, rồi mở API (cổng 8000) và web (cổng 3000). Dữ liệu demo nằm trong thư mục `demo_data/` (xóa đi để làm lại từ đầu).
Cần: Python 3.11+, Node 20.9+, đã `pip install -r requirements.txt` và `cd frontend && npm ci`.
"""

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "demo_data"
API_PORT = int(os.environ.get("DEMO_API_PORT", "8000"))  # đổi nếu cổng đã bị chương trình khác dùng
WEB_PORT = int(os.environ.get("DEMO_WEB_PORT", "3000"))
# Mật khẩu CỐ ĐỊNH, chỉ dành cho máy demo cục bộ (không dùng cho hệ thống thật).
ACCOUNTS = (
    ("an", "An (Engineer)", "engineer", "Demo-Engineer-2026"),
    ("binh", "Bình (Reviewer)", "reviewer", "Demo-Reviewer-2026"),
    ("quantri", "Quản trị", "admin", "Demo-Admin-2026"),
)


def demo_env() -> dict[str, str]:
    url = f"sqlite+pysqlite:///{(DATA / 'auth.db').as_posix()}"
    env = dict(os.environ)
    env.update(
        {
            "APP_ENV": "development",
            "NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS": "true",  # trang đăng nhập hiện tài khoản demo (chỉ bản demo cục bộ)
            "LLM_PROVIDER": "mock",
            "LLM_FALLBACK": "none",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "LANGCHAIN_TRACING_V2": "false",
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "DATABASE_URL": url,
            "MIGRATION_DATABASE_URL": url,
            "SESSION_SECRET": "demo-session-secret-chi-dung-cho-may-demo-0123456789",
            "SESSION_COOKIE_SECURE": "false",  # demo chạy bằng http://localhost
            "STORE_PATH": str(DATA / "app.db"),
            "CHECKPOINT_PATH": str(DATA / "checkpoints.db"),
            "SOURCES_DIR": str(DATA / "sources"),
            "WORKSPACES_DIR": str(DATA / "workspaces"),
            "DATA_DIR": str(DATA),
            "NEXT_PUBLIC_API_URL": f"http://localhost:{API_PORT}",
            "NEXT_TELEMETRY_DISABLED": "1",
        }
    )
    return env


def prepare_database(env: dict[str, str]) -> None:
    DATA.mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True)
    code = (
        "from src.services import auth\n"
        f"for u, n, r, p in {ACCOUNTS!r}:\n"
        "    if not auth.find_user(u):\n"
        "        auth.create_user(u, n, r, p)\n"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)


def wait_for(url: str, seconds: int) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            time.sleep(1.5)
    return False


def main() -> int:
    npm = shutil.which("npm")
    if not npm:
        print("Không thấy npm. Cài Node.js 20.9+ từ https://nodejs.org rồi chạy lại.")
        return 1
    if not (ROOT / "frontend" / "node_modules").exists():
        print("Chưa cài frontend. Chạy: cd frontend && npm ci   rồi chạy lại.")
        return 1
    env = demo_env()
    print("[1/3] Chuẩn bị cơ sở dữ liệu demo (SQLite)...")
    prepare_database(env)
    print("[2/3] Build giao diện (lần đầu mất khoảng 1–2 phút)...")
    subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", env=env, check=True, stdout=subprocess.DEVNULL)
    print("[3/3] Khởi động...")
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
        cwd=ROOT,
        env=env,
    )
    web = subprocess.Popen([npm, "run", "start", "--", "-p", str(WEB_PORT)], cwd=ROOT / "frontend", env=env)
    try:
        if not wait_for(f"http://127.0.0.1:{API_PORT}/health", 90):
            print("API không lên được, xem lỗi phía trên.")
            return 1
        print("\n" + "=" * 60)
        print(f"  Mở trình duyệt: http://localhost:{WEB_PORT}")
        print("  Tài khoản demo (mật khẩu cố định, chỉ dùng cho máy demo):")
        for user, _, role, password in ACCOUNTS:
            print(f"    {user:<8} {role:<9} mật khẩu: {password}")
        print("  Dừng: nhấn Ctrl+C")
        print("=" * 60)
        api.wait()
    except KeyboardInterrupt:
        print("\nĐang dừng...")
    finally:
        for proc in (web, api):
            proc.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
