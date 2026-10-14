"""Giải `secret_ref` (tên tham chiếu) thành giá trị thật — CHỈ gọi ở lớp kết nối (`src/services/connectors/`).

Giá trị thật không đi vào state, log, prompt, checkpoint hay phản hồi API. Nơi lưu: biến môi trường `P113_SECRET_<TÊN IN HOA>`
hoặc file `<SECRETS_DIR>/<tên>` (kiểu Docker/Kubernetes secrets). Thiếu thì báo lỗi tiếng Việt nêu TÊN biến cần đặt, không in giá trị.
"""

import os
from pathlib import Path

from src.config import get_settings
from src.models.sources import SECRET_REF_RE

ENV_PREFIX = (
    "P113_SECRET_"  # tiền tố này nằm trong danh sách biến bị lọc khỏi môi trường của dbt (dbt_tools.is_secret_env)
)


class SecretError(RuntimeError):
    """Không giải được tham chiếu bí mật. Thông báo tiếng Việt, không chứa giá trị."""


def env_name(secret_ref: str) -> str:
    """Tên biến môi trường chứa bí mật của `secret_ref`."""
    return f"{ENV_PREFIX}{secret_ref.upper()}"


def _file_for(secret_ref: str) -> Path | None:
    directory = get_settings().secrets_dir
    if not directory:
        return None
    path = (directory / secret_ref).resolve()
    return (
        path if path.parent == directory.resolve() and path.is_file() else None
    )  # không cho thoát khỏi thư mục bí mật


def resolve(secret_ref: str) -> str:
    """Giá trị thật của bí mật; SecretError (tiếng Việt, không in giá trị) nếu tham chiếu sai hoặc chưa cấu hình."""
    if not SECRET_REF_RE.fullmatch(secret_ref or ""):
        raise SecretError("Tên tham chiếu bí mật không hợp lệ (chỉ chữ, số, gạch dưới, bắt đầu bằng chữ).")
    value = os.environ.get(env_name(secret_ref), "")
    if not value and (path := _file_for(secret_ref)):
        value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise SecretError(
            f"Chưa cấu hình bí mật cho tham chiếu '{secret_ref}'. Quản trị viên cần đặt biến môi trường "
            f"{env_name(secret_ref)} (hoặc file cùng tên trong SECRETS_DIR) trên máy chủ."
        )
    return value


def is_configured(secret_ref: str) -> bool:
    """Đã có giá trị cho tham chiếu này chưa (không trả giá trị)."""
    try:
        resolve(secret_ref)
    except SecretError:
        return False
    return True
