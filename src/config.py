"""Cấu hình ứng dụng: mọi giá trị đọc từ biến môi trường / `.env`, có mặc định chạy được không cần khóa."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"
PLACEHOLDER_MARKERS = ("<", "your-", "sk-your", "-here")
# Trần token đầu ra theo node: ≥ 5 lần mức cao nhất đo được ở golden thật 2026-10-02 (planner 1.104, codegen 1.638,
# testgen 841, optimizer 295 — đã gồm token suy luận; trần 4.000 cũ từng bị dùng hết). Chỉnh lại sau khi có số đo mới.
# Optimizer 16.000: trần rộng từ thời dùng Opus (suy luận tính vào trần); Haiku không suy luận nên thực tế dùng ít hơn nhiều.
# input_gate: JSON rất ngắn (nhãn + độ tin cậy + vài ô thiếu) nên trần thấp (CLAUDE.md bản 2, mục 2).
TASK_MAX_TOKENS = {"planner": 6000, "codegen": 12000, "testgen": 5000, "optimizer": 16000, "input_gate": 200}
# Hạn chờ mỗi lượt gọi LLM (giây). Optimizer chỉ là bước tùy chọn nên hạn ngắn: treo thì bỏ qua sớm thay vì chờ nhiều phút.
TASK_TIMEOUT_SEC = {"planner": 120, "codegen": 180, "testgen": 120, "optimizer": 60, "input_gate": 30}
DEFAULT_TIMEOUT_SEC = 120
CODEGEN_MAX_TEMPERATURE = 0.2
MODELS_FILE = Path(__file__).resolve().parent.parent / "config" / "models.yaml"
INPUT_GATE_FILE = Path(__file__).resolve().parent.parent / "config" / "input_gate.yaml"
TASKS = ("planner", "codegen", "testgen", "optimizer")
GATE_TASK = "input_gate"  # bộ phân loại tầng 2 của cửa kiểm tra đầu vào: model riêng, rẻ nhất, không dùng model của planner/optimizer


def is_real_secret(value: str | None) -> bool:
    """True nếu giá trị đã được điền thật (không rỗng, không phải giá trị mẫu trong .env.example)."""
    return bool(value) and not any(marker in value for marker in PLACEHOLDER_MARKERS)


class ModelChoice(BaseModel):
    """Một dòng trong `config/models.yaml`: nhà cung cấp + tên model (+ mức effort cho Anthropic)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["openai", "anthropic", "google"]
    name: str = Field(min_length=1)
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    # false: model chỉ nhận nhiệt độ mặc định (vd gpt-6-luna từ chối temperature=0) → không gửi tham số này
    temperature: bool = True


class ModelTable(BaseModel):
    """Toàn bộ `config/models.yaml`: model của từng bước + model dự phòng."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    models: dict[Literal["planner", "codegen", "testgen", "optimizer", "input_gate"], ModelChoice]
    fallback: ModelChoice


@lru_cache
def load_model_table(path: Path = MODELS_FILE) -> ModelTable:
    """Đọc và kiểm tra `config/models.yaml` (thiếu bước nào thì báo lỗi ngay, không đoán model)."""
    table = ModelTable.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    missing = [
        task for task in TASKS if task not in table.models
    ]  # `input_gate` tùy chọn: thiếu thì dùng model dự phòng
    if missing:
        raise ValueError(f"{path} thiếu model cho bước: {', '.join(missing)}")
    return table


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

    # LLM — mặc định `mock` để chạy không cần khóa. `openai` = gọi model thật theo config/models.yaml (bước nào khai
    # báo anthropic thì gọi Anthropic); `google` = mọi bước dùng model dự phòng (Gemini).
    llm_provider: Literal["mock", "openai", "google"] = "mock"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    # Tên model KHÔNG nằm ở đây: chỉ khai báo trong config/models.yaml (CLAUDE.md mục 3)
    models_file: Path = MODELS_FILE
    # Dự phòng khi model chính gọi lỗi (model ở mục `fallback` của models.yaml)
    llm_fallback: Literal["none", "google"] = "google"
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)  # chỉ Codegen dùng (tối đa 0.2); node khác luôn 0
    llm_max_tokens: int = Field(default=16000, ge=256)  # trần chung; mỗi node có trần riêng ở TASK_MAX_TOKENS
    # Gửi JSON Schema của đầu ra (structured output); false = quay về chế độ json_object cũ
    llm_structured_output: bool = True
    # Circuit breaker cho mỗi cặp nhà cung cấp × model (src/services/circuit_breaker.py)
    breaker_min_calls: int = Field(default=4, ge=1)  # số lượt tối thiểu trong cửa sổ trước khi xét tỉ lệ lỗi
    breaker_failure_rate: float = Field(default=0.5, gt=0, le=1)  # tỉ lệ lỗi tối thiểu để ngắt mạch
    breaker_reset_sec: int = Field(default=60, ge=1)  # ngắt bao lâu rồi mới thử lại (OPEN → HALF_OPEN)
    breaker_probes: int = Field(default=1, ge=1, le=3)  # số lượt thăm dò thành công để đóng lại

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
    # Nơi lưu lần chạy, quyết định duyệt, sổ lỗi, bộ nhớ agent và checkpoint: sqlite (file trong data/) hoặc postgres (Neon,
    # dùng DATABASE_URL). Render xóa ổ đĩa khi khởi động lại nên triển khai thật dùng postgres.
    state_backend: Literal["sqlite", "postgres"] = "sqlite"
    # Số lần chạy đồng thời. SQLite chỉ an toàn với 1 luồng (một kết nối checkpoint); chỉ có tác dụng khi state_backend=postgres.
    run_workers: int = Field(default=2, ge=1, le=4)
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

    # Giới hạn theo người (CLAUDE.md mục 14): số lần chạy đang chờ/đang chạy; trần chi phí LLM mỗi ngày (0 = không chặn)
    max_active_runs_per_user: int = Field(default=2, ge=1)
    llm_daily_budget_usd: float = Field(default=1.0, ge=0.0)

    # Cửa kiểm tra đầu vào (tầng 0–2) + trần chi phí toàn hệ thống (CLAUDE.md bản 2, mục 1). Đặt 0 = không chặn.
    input_min_chars: int = Field(default=10, ge=1)
    input_max_chars: int = Field(default=2000, ge=10)
    input_gate_file: Path = INPUT_GATE_FILE
    input_gate_cache_size: int = Field(
        default=512, ge=0
    )  # số kết quả kiểm tra nhớ lại cho câu giống hệt (đã chuẩn hóa + băm)
    max_clarify_rounds: int = Field(
        default=2, ge=0
    )  # tối đa số vòng hỏi làm rõ mỗi lần chạy (J1 và hỏi bổ sung đầu vào)
    run_token_budget: int = Field(default=200_000, ge=0)  # trần token (vào + ra) mỗi lần chạy; vượt thì dừng và báo rõ
    user_daily_run_limit: int = Field(
        default=30, ge=0
    )  # số lần chạy tối đa mỗi người mỗi ngày (không tính lần bị chặn ở cửa kiểm tra)

    # Mức truy cập dữ liệu của LLM (CLAUDE.md bản 2, giai đoạn 3). Mặc định `profile` (thống kê, không dòng thật); đặt `schema_only`
    # để quay về quyết định ban đầu "chỉ cho xem schema". Nguồn `high` luôn bị ép về schema_only, `medium` tối đa profile.
    llm_access_default: Literal["schema_only", "profile", "masked_sample"] = "profile"
    llm_sample_max_rows: int = Field(default=5, ge=1, le=20)  # trần số dòng đã che ở mức masked_sample
    require_separate_reviewer: bool = True  # true: người tạo yêu cầu không tự duyệt được (ADR 0006, thay ADR 0004)
    secrets_dir: Path | None = None  # thư mục chứa bí mật dạng file (mỗi file một tên tham chiếu), tùy chọn

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

    @property
    def has_anthropic_key(self) -> bool:
        """Đã có ANTHROPIC_API_KEY thật."""
        return is_real_secret(self.anthropic_api_key)

    @property
    def model_table(self) -> ModelTable:
        """Bảng model đọc từ `models_file`."""
        return load_model_table(self.models_file)

    @property
    def google_model_name(self) -> str:
        """Model Gemini (mục `fallback` của models.yaml): dùng khi LLM_PROVIDER=google hoặc làm dự phòng."""
        return self.model_table.fallback.name

    def choice_for(self, task: str) -> ModelChoice:
        """Nhà cung cấp + model của một bước; LLM_PROVIDER=google thì mọi bước dùng model dự phòng."""
        if self.llm_provider == "google":
            return self.model_table.fallback
        table = self.model_table
        if task == GATE_TASK:  # bộ phân loại của cửa kiểm tra: model riêng, không mượn model của planner/optimizer
            return table.models.get(task, table.fallback)
        return table.models.get(task, table.models["planner"])

    def model_for(self, task: str, provider: str | None = None) -> str:
        """Tên model dùng cho một bước (planner/codegen/testgen/optimizer)."""
        if provider == "google":
            return self.google_model_name
        return self.choice_for(task).name

    @property
    def providers_in_use(self) -> set[str]:
        """Các nhà cung cấp mà bảng model đang cần (để kiểm tra khóa)."""
        return {self.choice_for(task).provider for task in (*TASKS, GATE_TASK)}

    def max_tokens_for(self, task: str) -> int:
        """Trần token đầu ra (gồm token suy luận ẩn) của một bước, không vượt LLM_MAX_TOKENS."""
        return min(TASK_MAX_TOKENS.get(task, self.llm_max_tokens), self.llm_max_tokens)

    def timeout_for(self, task: str) -> int:
        """Hạn chờ (giây) cho một lượt gọi LLM của bước `task`."""
        return TASK_TIMEOUT_SEC.get(task, DEFAULT_TIMEOUT_SEC)

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
        models = {task: self.model_for(task) for task in TASKS}
        if len(set(models.values())) == 1:
            return models["planner"]
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
