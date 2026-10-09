"""Cấu hình ứng dụng: mọi giá trị đọc từ biến môi trường / `.env`, có mặc định chạy được không cần khóa."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"
PLACEHOLDER_MARKERS = ("<", "your-", "sk-your", "-here")
# Trần token đầu ra theo node: ≥ 5 lần mức cao nhất đo được ở golden thật 2026-10-02 (planner 1.104, codegen 1.638,
# testgen 841, optimizer 295 — đã gồm token suy luận; trần 4.000 cũ từng bị dùng hết). Chỉnh lại sau khi có số đo mới.
TASK_MAX_TOKENS = {"planner": 6000, "codegen": 12000, "testgen": 5000, "optimizer": 4000}
CODEGEN_MAX_TEMPERATURE = 0.2


def is_real_secret(value: str | None) -> bool:
    """True nếu giá trị đã được điền thật (không rỗng, không phải giá trị mẫu trong .env.example)."""
    return bool(value) and not any(marker in value for marker in PLACEHOLDER_MARKERS)


class Settings(BaseSettings):
    """Cấu hình toàn hệ thống (API, CLI, graph dùng chung)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "P-113 Pipeline Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # LLM — mặc định `mock` để chạy không cần khóa
    llm_provider: Literal["mock", "openai", "google"] = "mock"
    openai_api_key: str = ""
    google_api_key: str = ""
    # Model OpenAI theo từng bước (hướng C). MODEL_NAME là model chính; để trống MODEL_<BƯỚC> thì dùng MODEL_NAME.
    model_name: str = "gpt-5.6-luna"
    model_planner: str = ""
    model_codegen: str = ""
    model_testgen: str = ""
    model_optimizer: str = "gpt-5.6-terra"
    # Google Gemini: dùng khi LLM_PROVIDER=google, hoặc làm dự phòng khi OpenAI lỗi (LLM_FALLBACK=google)
    google_model_name: str = "gemini-3.1-flash-lite"
    llm_fallback: Literal["none", "google"] = "google"
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)  # chỉ Codegen dùng (tối đa 0.2); node khác luôn 0
    llm_max_tokens: int = Field(default=16000, ge=256)  # trần chung; mỗi node có trần riêng ở TASK_MAX_TOKENS
    # Gửi JSON Schema của đầu ra (structured output); false = quay về chế độ json_object cũ
    llm_structured_output: bool = True

    # Đăng nhập + cơ sở dữ liệu ứng dụng (PostgreSQL). Chuỗi kết nối và khóa CHỈ đọc từ biến môi trường / .env.
    # DATABASE_URL = tài khoản ứng dụng (không phải superuser); MIGRATION_DATABASE_URL chỉ dùng khi chạy Alembic.
    database_url: str = ""
    migration_database_url: str = ""
    db_app_role: str = Field(default="p113_app", pattern=r"^[a-z_][a-z0-9_]{0,62}$")  # migration cấp quyền cho role này
    session_secret: str = ""  # ≥ 32 ký tự ngẫu nhiên; xoay vòng = mọi phiên cũ mất hiệu lực
    session_ttl_minutes: int = Field(default=480, ge=5, le=1440)  # một ngày làm việc
    session_cookie_secure: bool = True  # chỉ tắt khi thử qua IP mạng nội bộ bằng http
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    login_max_failures: int = Field(default=5, ge=1)
    login_lock_minutes: int = Field(default=15, ge=1)
    force_https: bool = False  # true khi triển khai: chuyển hướng HTTP → HTTPS

    # Lưu trữ
    data_dir: Path = Path("./data")
    sources_dir: Path = Path("./data/sources")
    store_path: Path = Path("./data/app.db")
    checkpoint_path: Path = Path("./data/checkpoints.db")
    template_dir: Path = Path("./pipelines/template")
    workspaces_dir: Path = Path("./pipelines/workspaces")

    # Sandbox (V2)
    sandbox_timeout_sec: int = Field(default=300, ge=10)
    sandbox_memory_limit: str = "1GB"
    sandbox_threads: int = Field(default=2, ge=1)

    # Giới hạn vòng lặp agent
    max_fix_attempts: int = Field(default=3, ge=1)
    max_plan_rounds: int = Field(default=5, ge=1)
    max_review_rounds: int = Field(default=3, ge=1)

    # Dữ liệu thử (E2)
    seed: int = 42
    mock_small_rows: int = Field(default=200, ge=10)
    mock_large_rows: int = Field(default=300_000, ge=1000)

    # Optimizer (E4) + Đối chiếu (V3)
    opt_min_gain_pct: float = Field(default=15.0, ge=0.0)
    opt_runs_per_month: int = Field(default=30, ge=1)
    opt_compute_cost_per_hour_usd: float = Field(default=0.5, ge=0.0)
    opt_max_attempts: int = Field(default=3, ge=1)
    opt_bench_runs: int = Field(default=5, ge=1)
    compare_abs_tol: float = Field(default=1e-6, ge=0.0)

    # LangSmith (tùy chọn)
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langsmith_api_key: str = ""

    @property
    def has_openai_key(self) -> bool:
        """Đã có OPENAI_API_KEY thật."""
        return is_real_secret(self.openai_api_key)

    @property
    def has_google_key(self) -> bool:
        """Đã có GOOGLE_API_KEY thật."""
        return is_real_secret(self.google_api_key)

    def model_for(self, task: str, provider: str | None = None) -> str:
        """Model dùng cho một bước (planner/codegen/testgen/optimizer) với nhà cung cấp đã chọn."""
        if (provider or self.llm_provider) == "google":
            return self.google_model_name
        override = {
            "planner": self.model_planner,
            "codegen": self.model_codegen,
            "testgen": self.model_testgen,
            "optimizer": self.model_optimizer,
        }.get(task, "")
        return override or self.model_name

    def max_tokens_for(self, task: str) -> int:
        """Trần token đầu ra (gồm token suy luận ẩn) của một bước, không vượt LLM_MAX_TOKENS."""
        return min(TASK_MAX_TOKENS.get(task, self.llm_max_tokens), self.llm_max_tokens)

    def temperature_for(self, task: str) -> float:
        """Planner/Testgen/Optimizer = 0 (tất định); Codegen = LLM_TEMPERATURE nhưng không quá 0.2."""
        return min(self.llm_temperature, CODEGEN_MAX_TEMPERATURE) if task == "codegen" else 0.0

    @property
    def models_summary(self) -> str:
        """Mô tả ngắn model đang dùng (ghi vào báo cáo/lần chạy)."""
        if self.is_mock:
            return "mock"
        if self.llm_provider == "google":
            return self.google_model_name
        tasks = ("planner", "codegen", "testgen", "optimizer")
        models = {task: self.model_for(task) for task in tasks}
        if len(set(models.values())) == 1:
            return self.model_name
        return ", ".join(f"{task}={model}" for task, model in models.items())

    @property
    def has_langsmith_key(self) -> bool:
        """Đã có khóa LangSmith thật (chấp nhận cả tên LANGCHAIN_* lẫn LANGSMITH_*)."""
        return is_real_secret(self.langchain_api_key) or is_real_secret(self.langsmith_api_key)

    @property
    def missing_auth_settings(self) -> list[str]:
        """Tên biến môi trường còn thiếu để bật đăng nhập (không bao giờ trả giá trị)."""
        missing = [] if self.database_url else ["DATABASE_URL"]
        return missing + ([] if len(self.session_secret) >= 32 else ["SESSION_SECRET"])

    @property
    def is_mock(self) -> bool:
        """True khi đang chạy chế độ mô phỏng (LLM giả)."""
        return self.llm_provider == "mock"


@lru_cache
def get_settings() -> Settings:
    """Trả về cấu hình dùng chung (cache một lần)."""
    return Settings()
