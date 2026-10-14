"""Giao diện chung của bộ nạp nguồn (CLAUDE.md bản 2, giai đoạn 4): tách "lấy dữ liệu" khỏi lõi agent.

Hai nhóm hàm tương ứng hai đường dữ liệu:

- **Cho LLM** (chỉ trả thứ đã được phép; đi qua `llm_context.build_llm_context`): `list_tables`, `get_schema`,
  `get_schema_fingerprint`, `get_profile` (số đếm + dạng giá trị, không giá trị thật), `sample` (CHỈ khi mức `masked_sample`).
- **Cho code** (không trả dòng dữ liệu về phía LLM): `load_to_sandbox` (nạp một tập con có hạt giống cố định vào DuckDB sandbox,
  cột nhạy cảm của nguồn `high` được thay bằng giá trị băm có muối, nhất quán giữa các bảng để JOIN còn đúng), `health_check`.

Mỗi connector chỉ nhận `DataSource` đã được lọc quyền (giai đoạn 3), không tự truy cập sổ nguồn, và chỉ thấy bảng trong
`allowed_tables`.
"""

import hashlib
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Literal

import duckdb
from pydantic import BaseModel, ConfigDict, Field

from src.agents.tools.pii import mask_value, sensitive_column, value_shape
from src.config import get_settings
from src.models.sources import DataSource

NormalizedType = Literal["integer", "decimal", "float", "string", "boolean", "date", "timestamp", "json", "other"]
HASH_PREFIX = "h_"
HASH_LENGTH = 16

TYPE_WORDS: dict[str, NormalizedType] = {
    "TINYINT": "integer", "SMALLINT": "integer", "INT": "integer", "INTEGER": "integer", "BIGINT": "integer",
    "HUGEINT": "integer", "UBIGINT": "integer", "INT2": "integer", "INT4": "integer", "INT8": "integer",
    "SERIAL": "integer", "BIGSERIAL": "integer", "SMALLSERIAL": "integer",
    "DECIMAL": "decimal", "NUMERIC": "decimal", "MONEY": "decimal",
    "DOUBLE": "float", "FLOAT": "float", "REAL": "float", "FLOAT4": "float", "FLOAT8": "float",
    "VARCHAR": "string", "TEXT": "string", "CHAR": "string", "CHARACTER": "string", "BPCHAR": "string", "STRING": "string",
    "UUID": "string", "CITEXT": "string", "NAME": "string",
    "BOOLEAN": "boolean", "BOOL": "boolean",
    "DATE": "date",
    "TIMESTAMP": "timestamp", "TIMESTAMPTZ": "timestamp", "DATETIME": "timestamp",
    "JSON": "json", "JSONB": "json", "STRUCT": "json", "MAP": "json",
}  # fmt: skip


def normalize_type(raw: str) -> NormalizedType:
    """Kiểu của DuckDB/PostgreSQL/SQLite quy về tập nhỏ: integer, decimal, float, string, boolean, date, timestamp, json, other.

    `TIMESTAMP WITH TIME ZONE`, `DECIMAL(18,3)`, `CHARACTER VARYING(20)`, `INTEGER[]` đều nhận ra theo từ đầu; kiểu mảng là `other`.
    """
    text = (raw or "").strip().upper()
    if text.endswith("[]") or text.startswith("ARRAY"):
        return "other"
    word = re.split(r"[\s(\[]", text, maxsplit=1)[0]
    return TYPE_WORDS.get(word, "other")


class TableSchema(BaseModel):
    """Cấu trúc một bảng: tên, cột → kiểu (nguyên văn của nguồn), cột khóa gợi ý (chỉ tên)."""

    name: str
    columns: dict[str, str]


class SchemaFingerprint(BaseModel):
    """Cấu trúc chuẩn hóa của một tập bảng + mã băm: so hai dấu vân tay là biết cấu trúc nguồn có đổi không (giai đoạn 5)."""

    tables: dict[str, dict[str, str]]  # bảng → cột → kiểu chuẩn hóa
    digest: str

    @classmethod
    def build(cls, tables: dict[str, dict[str, str]]) -> "SchemaFingerprint":
        canonical = "|".join(
            f"{t}:" + ",".join(f"{c}={ty}" for c, ty in sorted(cols.items())) for t, cols in sorted(tables.items())
        )
        return cls(tables=tables, digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest())


class TableProfile(BaseModel):
    """Hồ sơ thống kê một bảng: số đếm và dạng giá trị, KHÔNG có giá trị thật (xem `services/profiling.py`)."""

    model_config = ConfigDict(extra="allow")

    rows: int = 0
    columns: dict[str, dict] = Field(default_factory=dict)


class HealthResult(BaseModel):
    """Kết quả kiểm tra kết nối; `message` tiếng Việt thân thiện, đã qua `scrub_error`."""

    ok: bool
    message: str


class ConnectorError(RuntimeError):
    """Lỗi của bộ nạp, thông báo tiếng Việt, không chứa bí mật hay giá trị dữ liệu."""


class TableNotAllowedError(ConnectorError):
    """Bảng không nằm trong `allowed_tables` hoặc không tồn tại (cùng một thông báo, không lộ bảng có tồn tại hay không)."""


class SampleNotAllowedError(ConnectorError):
    """Nguồn không cho LLM xem dòng mẫu (mức truy cập khác `masked_sample`)."""


NOT_ALLOWED = "Bảng này không có trong danh sách được phép của nguồn hoặc không tồn tại."


class SourceConnector(ABC):
    """Lớp cơ sở. Lớp con cài các hàm trừu tượng; kiểm quyền bảng, kiểm mức mẫu và băm cột nhạy cảm dùng chung ở đây."""

    def __init__(self, source: DataSource) -> None:
        self.source = source

    # ---------- Nhóm cho LLM ----------

    @abstractmethod
    def list_tables(self) -> list[str]:
        """Tên các bảng được phép (đã lọc theo `allowed_tables`)."""

    @abstractmethod
    def get_schema(self, table: str) -> TableSchema:
        """Cột và kiểu của một bảng được phép (TableNotAllowedError nếu không được phép)."""

    def get_schema_fingerprint(self, tables: list[str] | None = None) -> SchemaFingerprint:
        """Cấu trúc chuẩn hóa + mã băm của các bảng được phép (mặc định: tất cả)."""
        names = tables if tables is not None else self.list_tables()
        normalized = {
            name: {c: normalize_type(t) for c, t in self.get_schema(name).columns.items()} for name in sorted(names)
        }
        return SchemaFingerprint.build(normalized)

    @abstractmethod
    def get_profile(self, table: str) -> TableProfile:
        """Thống kê và dạng giá trị theo mục 3.3; cột nhạy cảm bỏ min/max và giá trị phổ biến."""

    def row_count(self, table: str) -> int | None:
        """Số dòng của bảng cho CODE dùng (chọn nạp toàn bộ/phần mới); không đi vào prompt. Mặc định lấy từ hồ sơ; lỗi → None."""
        try:
            return int(self.get_profile(table).rows)
        except (ConnectorError, KeyError):
            return None

    def sample(self, table: str, n: int) -> list[dict]:
        """Tối đa `n` dòng ĐÃ CHE (cột nhạy cảm chỉ còn dạng giá trị). Chỉ khi nguồn ở mức `masked_sample`, ngược lại ném lỗi."""
        if self.source.effective_llm_access != "masked_sample":
            raise SampleNotAllowedError("Nguồn này không cho AI xem dòng mẫu (chỉ mức 'masked_sample' mới được).")
        self.require_table(table)
        limit = max(0, min(int(n), get_settings().llm_sample_max_rows))
        names, rows = self._read_rows(table, limit)
        restricted = self.source.restricted_columns
        return [
            {
                name: value_shape(str(value))
                if sensitive_column(name, restricted) and value is not None
                else mask_value(_plain(value))
                for name, value in zip(names, row, strict=True)
            }
            for row in rows
        ]

    @abstractmethod
    def _read_rows(self, table: str, n: int) -> tuple[list[str], list[tuple]]:
        """Đọc `n` dòng đầu của bảng (chỉ nội bộ, không bao giờ trả thẳng ra ngoài mà không che)."""

    # ---------- Nhóm cho code ----------

    @abstractmethod
    def load_to_sandbox(
        self, tables: list[str], sandbox_conn: duckdb.DuckDBPyConnection, max_rows: int
    ) -> dict[str, int]:
        """Nạp các bảng vào schema `raw` của sandbox DuckDB (tối đa `max_rows` dòng mỗi bảng, hạt giống cố định).
        Chỉ trả SỐ DÒNG đã nạp, không trả dòng dữ liệu."""

    @abstractmethod
    def health_check(self) -> HealthResult:
        """Kiểm tra kết nối, trả lỗi tiếng Việt thân thiện (đã qua scrub_error)."""

    @abstractmethod
    def catalog(self) -> list[dict]:
        """Danh mục cho sổ nguồn: mỗi bảng được phép một dict (name, kind, columns, label, path, table). Không có dòng dữ liệu."""

    # ---------- Dùng chung ----------

    def require_table(self, table: str) -> None:
        """Bảng phải được phép; sai thì ném TableNotAllowedError (cùng thông báo cho bảng không có và bảng ngoài quyền)."""
        if table not in self.list_tables():
            raise TableNotAllowedError(NOT_ALLOWED)

    def columns_to_hash(self, columns: Iterable[str]) -> list[str]:
        """Cột nhạy cảm sẽ băm khi nạp sandbox. `SANDBOX_HASH_SENSITIVE`: `auto` (mặc định) chỉ với nguồn độ nhạy cảm `high`,
        `always` mọi nguồn, `never` không băm."""
        mode = get_settings().sandbox_hash_sensitive
        if mode == "never" or (mode == "auto" and self.source.sensitivity != "high"):
            return []
        return [c for c in columns if sensitive_column(c, self.source.restricted_columns)]


def _plain(value: object) -> object:
    return value if isinstance(value, str | int | float | type(None)) else str(value)


def quote(identifier: str) -> str:
    """Tên định danh SQL có dấu nháy kép an toàn."""
    return '"' + identifier.replace('"', '""') + '"'


def pseudonymize(con: duckdb.DuckDBPyConnection, table: str, columns: list[str]) -> list[str]:
    """Thay các cột bằng `h_<16 ký tự hex>` = băm SHA-256 có muối của giá trị: cùng giá trị → cùng mã ở MỌI bảng (JOIN còn đúng),
    NULL giữ NULL. Muối: `SANDBOX_HASH_SALT`. Cột số được đổi sang VARCHAR trước. Trả về danh sách cột đã băm."""
    salt = get_settings().sandbox_hash_salt or "p113-sandbox"
    present = {
        row[0]
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='raw' AND table_name=?", [table]
        ).fetchall()
    }
    done = []
    for column in columns:
        if column not in present:
            continue
        col = quote(column)
        con.execute(f"ALTER TABLE raw.{quote(table)} ALTER {col} SET DATA TYPE VARCHAR")
        con.execute(
            f"UPDATE raw.{quote(table)} SET {col} = CASE WHEN {col} IS NULL THEN NULL "
            f"ELSE '{HASH_PREFIX}' || substr(sha256(? || {col}), 1, {HASH_LENGTH}) END",
            [salt],
        )
        done.append(column)
    return done
