"""Hợp đồng `PipelineSpec` (đầu ra của Planner) và hàm tất định `decide_mode`."""

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

TABULAR_KINDS = {"csv", "json", "parquet", "sqlite", "duckdb", "postgres"}  # duckdb/postgres: nguồn từ bộ nạp CSDL


class PipelineMode(StrEnum):
    """Kiểu pipeline: biến đổi trong kho (ELT), trước khi nạp (ETL) hoặc kết hợp."""

    ELT = "ELT"
    ETL = "ETL"
    HYBRID = "HYBRID"


class SourceRef(BaseModel):
    """Một nguồn dữ liệu được dùng trong pipeline."""

    name: str = Field(..., description="Tên bảng raw, ví dụ `shopee_orders`")
    kind: str = Field(..., description="csv | json | parquet | sqlite | duckdb | postgres | image | pdf")
    path: str = Field(default="", description="Đường dẫn file nguồn")


class Metric(BaseModel):
    """Chỉ số cần tính, mô tả bằng lời thường."""

    name: str
    description: str


class OutputColumn(BaseModel):
    """Một cột của bảng đích — hợp đồng chung cho Codegen và Testgen."""

    name: str
    type: str = Field(..., description="Kiểu SQL, ví dụ DATE, BIGINT, VARCHAR")
    description: str = ""
    references: str = Field(default="", description="Khóa ngoại dạng `bang.cot` nếu có")


class ClarifyQuestion(BaseModel):
    """Câu hỏi làm rõ dạng trắc nghiệm (J1).

    Câu hỏi về giá trị của một cột (`column`): code thay lựa chọn của LLM bằng giá trị thật của cột để người tick
    nhiều ô (`multiple`); LLM chỉ thấy giá trị người đã chọn (CLAUDE.md 2.3).
    """

    id: str
    question: str
    options: list[str] = Field(..., min_length=2)
    column: str = Field(default="", description="nguồn.cột khi lựa chọn là giá trị thật của cột")
    multiple: bool = False
    normalized: bool = Field(default=False, description="giá trị đã gộp theo upper(trim(...))")


class PlanStep(BaseModel):
    """Một bước trong kế hoạch, viết bằng lời thường để DE duyệt trước khi sinh code (J1b)."""

    title: str = Field(..., description="Tên bước ngắn gọn, ví dụ 'Làm sạch đơn Shopee'")
    detail: str = Field(default="", description="Làm gì, với bảng/cột nào")
    reason: str = Field(default="", description="Vì sao cần bước này (dựa trên yêu cầu hoặc dữ liệu thấy được)")


class ModeSignals(BaseModel):
    """Tín hiệu để chọn ELT/ETL. LLM chỉ giúp rút tín hiệu, quyết định là code."""

    restricted_pii: bool = Field(default=False, description="Có dữ liệu cá nhân không được vào kho nguyên bản")
    non_tabular_source: bool = Field(default=False, description="Có nguồn không phải bảng (ảnh, PDF)")
    tabular_source: bool = Field(default=True, description="Có nguồn dạng bảng")
    small_subset_of_large: bool = Field(default=False, description="Chỉ cần phần rất nhỏ của dữ liệu lớn")


LoadMode = Literal["full", "incremental"]
Schedule = Literal["hourly", "daily", "event"]
LOAD_LABELS = {"full": "Nạp toàn bộ mỗi lần chạy", "incremental": "Chỉ nạp phần mới (theo cột thời gian)"}
SCHEDULE_LABELS = {"hourly": "Hằng giờ", "daily": "Hằng ngày", "event": "Theo sự kiện (kích hoạt từ bên ngoài)"}
CONNECTION_TEXT = {
    "file": "đọc tệp trong thư mục dữ liệu",
    "duckdb": "kết nối DuckDB chỉ đọc",
    "postgres": "kết nối PostgreSQL chỉ đọc (tài khoản chỉ có quyền SELECT)",
}
INCREMENTAL_MIN_ROWS = 100_000  # từ chừng này dòng trở lên mới gợi ý nạp phần mới
PREFERRED_TIME_COLUMNS = ("updated_at", "modified_at", "last_modified", "created_at", "event_time", "timestamp")
TIME_COLUMN_RE = re.compile(
    r"(updated|modified|created|event)(_at|_on|_ts|_time|_date)$|_at$|_ts$|^timestamp$", re.IGNORECASE
)
HOURLY_RE = re.compile(r"moi gio|hang gio|hourly|moi 1 gio|every hour", re.IGNORECASE)
EVENT_RE = re.compile(r"khi co su kien|theo su kien|su kien|event|real.?time|realtime|ngay khi", re.IGNORECASE)


class SourceConnection(BaseModel):
    """Cách pipeline lấy dữ liệu của một nguồn (lấy từ sổ nguồn, code điền)."""

    source: str
    kind: str
    via: str


class PipelineOptions(BaseModel):
    """Lựa chọn pipeline do code đề xuất kèm lý do bằng lời thường; DE chọn hoặc chấp nhận mặc định ở J1b. Dữ liệu CÓ CẤU TRÚC để
    Coder và V0 dùng (các trường `*_reason` chỉ để người đọc, không gửi LLM)."""

    load_mode: LoadMode = "full"
    load_reason: str = ""
    incremental_column: str = ""
    schedule: Schedule = "daily"
    schedule_reason: str = ""
    connections: list[SourceConnection] = Field(default_factory=list)


class GlossaryUse(BaseModel):
    """Thuật ngữ nghiệp vụ Planner được cung cấp cho yêu cầu này (code chọn, hiện ở J1b để DE biết kế hoạch dựa vào định nghĩa nào)."""

    term: str
    definition: str = ""


class PipelineSpec(BaseModel):
    """Đặc tả pipeline do Planner lập; V0 soát trước khi sinh code."""

    request_text: str
    mode: PipelineMode = PipelineMode.ELT
    mode_reason: str = ""
    sources: list[SourceRef] = Field(default_factory=list)
    target: str = Field(default="", description="Tên bảng đích (model dbt cuối)")
    grain: list[str] = Field(default_factory=list, description="Các cột xác định một dòng của bảng đích")
    output_columns: list[OutputColumn] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    decisions: dict[str, str] = Field(default_factory=dict, description="Câu trả lời J1: id câu hỏi → lựa chọn")
    signals: ModeSignals = Field(default_factory=ModeSignals)
    plan_summary: str = Field(default="", description="Tóm tắt kế hoạch 1–3 câu cho người không rành kỹ thuật")
    plan: list[PlanStep] = Field(default_factory=list, description="Các bước sẽ làm, có giải thích (DE duyệt ở J1b)")
    options: PipelineOptions = Field(
        default_factory=PipelineOptions, description="Lựa chọn pipeline (nạp, lịch, kết nối)"
    )
    glossary_used: list[GlossaryUse] = Field(
        default_factory=list, description="Thuật ngữ từ điển nghiệp vụ đã cung cấp"
    )


def signals_from_sources(sources: list[SourceRef], signals: ModeSignals) -> ModeSignals:
    """Tính lại tín hiệu loại nguồn bằng code (không tin LLM cho phần đo được)."""
    kinds = {s.kind for s in sources}
    return signals.model_copy(
        update={
            "tabular_source": bool(kinds & TABULAR_KINDS),
            "non_tabular_source": bool(kinds - TABULAR_KINDS),
        }
    )


def decide_mode(signals: ModeSignals) -> tuple[PipelineMode, str]:
    """Chọn ELT/ETL/HYBRID theo luật cố định; trả về (mode, lý do)."""
    if signals.non_tabular_source and signals.tabular_source:
        return PipelineMode.HYBRID, "Có nguồn không phải bảng (xử lý ETL cục bộ) và nguồn dạng bảng (ELT)."
    if signals.non_tabular_source:
        return PipelineMode.ETL, "Nguồn không phải bảng (ảnh/PDF) phải trích xuất trước khi nạp."
    if signals.restricted_pii:
        return (
            PipelineMode.ETL,
            "ETL: biến đổi trước khi nạp, vì có dữ liệu cá nhân không được vào kho nguyên bản; phải che/lọc trước.",
        )
    if signals.small_subset_of_large:
        return (
            PipelineMode.ETL,
            "ETL: lọc trước khi nạp, vì chỉ cần một phần rất nhỏ của dữ liệu lớn nên nạp hết là lãng phí.",
        )
    return (
        PipelineMode.ELT,
        "Mặc định ELT: nạp dữ liệu thô vào kho trước rồi biến đổi bằng dbt (giữ nguyên bản gốc nên chạy lại được khi cần vá).",
    )


def _normalized(text: str) -> str:
    import unicodedata

    plain = "".join(
        c
        for c in unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", plain.lower())


def pick_time_column(columns: list[str]) -> str:
    """Cột thời gian để nạp phần mới: ưu tiên updated_at > modified_at > created_at...; không có cột nào khớp thì rỗng."""
    lowered = {c.lower(): c for c in columns}
    for name in PREFERRED_TIME_COLUMNS:
        if name in lowered:
            return lowered[name]
    return next((c for c in columns if TIME_COLUMN_RE.search(c)), "")


def decide_options(
    request_text: str, sources: list[dict], rows: dict[str, int | None], overrides: dict[str, str] | None = None
) -> PipelineOptions:
    """Đề xuất lựa chọn pipeline bằng luật cố định (0 token) kèm lý do bằng lời thường.

    - Nạp: bảng lớn (≥ `INCREMENTAL_MIN_ROWS` dòng) có cột thời gian → nạp phần mới theo cột đó; còn lại nạp toàn bộ.
    - Lịch: yêu cầu nêu "mỗi giờ" → hằng giờ; nêu sự kiện → theo sự kiện; mặc định hằng ngày. DAG chỉ ghi lịch, không chạy thật.
    - Kết nối: loại nguồn lấy từ sổ nguồn.
    `overrides`: lựa chọn DE đã đặt ở J1b (giữ nguyên khi Planner lập lại kế hoạch).
    """
    text = _normalized(request_text)
    schedule: Schedule = "hourly" if HOURLY_RE.search(text) else "event" if EVENT_RE.search(text) else "daily"
    schedule_reason = {
        "hourly": "Yêu cầu nêu cần cập nhật mỗi giờ.",
        "event": "Yêu cầu nêu chạy khi có sự kiện: DAG không đặt lịch, được kích hoạt từ bên ngoài.",
        "daily": "Yêu cầu không nêu tần suất nên chọn mặc định hằng ngày.",
    }[schedule]
    known = [(item, rows.get(item["name"])) for item in sources]
    largest, count = max(known, key=lambda pair: pair[1] or 0, default=({}, None))
    column = pick_time_column(list(largest.get("columns", {}))) if largest else ""
    if count is None and known:
        mode, reason = "full", "Chưa đo được số dòng của nguồn nên nạp toàn bộ mỗi lần chạy cho chắc."
    elif count is not None and count >= INCREMENTAL_MIN_ROWS and column:
        mode = "incremental"
        reason = (
            f"Bảng {largest['name']} có {count:,} dòng và cột thời gian {column}: chỉ nạp phần mới theo {column} cho chạy nhanh; "
            "khi sửa logic cần chạy nạp toàn bộ một lần."
        )
    elif count is not None and count >= INCREMENTAL_MIN_ROWS:
        mode, reason = (
            "full",
            f"Bảng {largest['name']} lớn ({count:,} dòng) nhưng không có cột thời gian để biết phần mới nên nạp toàn bộ.",
        )
    else:
        mode, reason = (
            "full",
            f"Dữ liệu còn nhỏ (dưới {INCREMENTAL_MIN_ROWS:,} dòng) nên nạp toàn bộ mỗi lần: đơn giản và không bỏ sót dòng bị sửa.",
        )
    options = PipelineOptions(
        load_mode=mode,
        load_reason=reason,
        incremental_column=column if mode == "incremental" else "",
        schedule=schedule,
        schedule_reason=schedule_reason,
        connections=[
            SourceConnection(
                source=item["name"],
                kind=item.get("source_kind") or item.get("kind", ""),
                via=CONNECTION_TEXT.get(item.get("source_kind") or "file", CONNECTION_TEXT["file"]),
            )
            for item in sources
        ],
    )
    return apply_overrides(options, overrides or {}, [list(i.get("columns", {})) for i in sources])


def apply_overrides(options: PipelineOptions, choice: dict[str, str], column_sets: list[list[str]]) -> PipelineOptions:
    """Áp lựa chọn của DE (chỉ nhận giá trị hợp lệ; cột thời gian phải có thật ở một nguồn)."""
    update: dict[str, str] = {}
    if choice.get("load_mode") in LOAD_LABELS:
        update["load_mode"] = choice["load_mode"]
        update["load_reason"] = f"Bạn chọn: {LOAD_LABELS[choice['load_mode']]}."
    if choice.get("schedule") in SCHEDULE_LABELS:
        update["schedule"] = choice["schedule"]
        update["schedule_reason"] = f"Bạn chọn: {SCHEDULE_LABELS[choice['schedule']]}."
    wanted = choice.get("incremental_column", "")
    if wanted and any(wanted in columns for columns in column_sets):
        update["incremental_column"] = wanted
    merged = options.model_copy(update=update)
    if merged.load_mode == "full":
        merged = merged.model_copy(update={"incremental_column": ""})
    return merged
