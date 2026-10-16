"""Khung Extract chung với 3 bộ nạp (CLAUDE.md bản 2, giai đoạn 4): cùng một bộ test hợp đồng cho tệp, DuckDB và PostgreSQL.

Test PostgreSQL chỉ chạy khi `RUN_PG_TESTS=1` (CI mặc định bỏ qua): dùng `PG_SOURCE_DSN` nếu có, nếu không dùng
`TEST_DATABASE_URL` (tạo một schema riêng rồi xóa). Cách chạy: docs/RUNBOOK.md, mục "Thử nguồn PostgreSQL".
"""

import csv
import json
import os
import uuid
from pathlib import Path

import duckdb
import pytest

from src.config import get_settings
from src.models.sources import DataSource
from src.services import secrets
from src.services.connectors import (
    ConnectorError,
    SampleNotAllowedError,
    TableNotAllowedError,
    get_connector,
    normalize_type,
)
from src.services.connectors.base import NOT_ALLOWED
from src.services.connectors.postgres import PostgresConnector, ReadOnlyViolationError, check_select

RUN_PG = os.environ.get("RUN_PG_TESTS") == "1"
CUSTOMERS = [
    (1, "canary.1@secret-corp.vn", "0987654321", "Nguyễn Canary Một", "Hà Nội"),
    (2, "canary.2@secret-corp.vn", "0912345678", "Trần Canary Hai", "HCM"),
    (3, "canary.3@secret-corp.vn", "0933333333", "Lê Canary Ba", "Hà Nội"),
    (4, "canary.4@secret-corp.vn", "0944444444", "Phạm Canary Bốn", "HCM"),
    (5, "canary.5@secret-corp.vn", "0955555555", "Hoàng Canary Năm", "Hà Nội"),
    (6, "canary.6@secret-corp.vn", "0966666666", "Vũ Canary Sáu", "HCM"),
]
ORDERS = [
    (100 + i, CUSTOMERS[i % 6][1], 100.5 * (i + 1), ("completed", "cancelled", "refunded")[i % 3]) for i in range(10)
]
CANARIES = [v for row in CUSTOMERS for v in row[1:4]]
BACKENDS = [
    "file",
    "duckdb",
    pytest.param("postgres", marks=pytest.mark.skipif(not RUN_PG, reason="cần RUN_PG_TESTS=1")),
]


def make_source(kind: str, secret_ref: str = "", **overrides) -> DataSource:
    fields = {
        "id": 1, "name": f"nguon-{kind}", "department_id": 1, "kind": kind, "secret_ref": secret_ref,
        "allowed_tables": ["*"], "sensitivity": "medium", "llm_access": "profile",
    }  # fmt: skip
    return DataSource(**{**fields, **overrides})


def _write_csv(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, header, rows in (
        ("customers", ["id", "email", "phone", "full_name", "city"], CUSTOMERS),
        ("orders", ["order_id", "customer_email", "total", "status"], ORDERS),
    ):
        with (directory / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)


def _write_duckdb(path: Path) -> None:
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE TABLE customers (id BIGINT, email VARCHAR, phone VARCHAR, full_name VARCHAR, city VARCHAR)")
        con.execute("CREATE TABLE orders (order_id BIGINT, customer_email VARCHAR, total DOUBLE, status VARCHAR)")
        con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", CUSTOMERS)
        con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", ORDERS)


def _pg_dsn() -> str:
    from tests.conftest import TEST_DATABASE_URL

    return os.environ.get("PG_SOURCE_DSN") or TEST_DATABASE_URL


@pytest.fixture
def backend(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`backend(**overrides)` → connector cùng dữ liệu (customers, orders) trên nền tệp / DuckDB / PostgreSQL."""
    kind = request.param
    cleanup = []
    default_tables = ["*"]
    if kind == "file":
        _write_csv(tmp_path / "files")
        monkeypatch.setenv(secrets.env_name("conn_test_file"), str(tmp_path / "files"))
        ref = "conn_test_file"
    elif kind == "duckdb":
        _write_duckdb(tmp_path / "source.duckdb")
        monkeypatch.setenv(secrets.env_name("conn_test_duck"), str(tmp_path / "source.duckdb"))
        ref = "conn_test_duck"
    else:
        import psycopg
        from psycopg.conninfo import make_conninfo

        schema = f"p113_src_{uuid.uuid4().hex[:8]}"
        dsn = _pg_dsn().replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(dsn, autocommit=True) as conn:
            try:
                conn.execute(f'CREATE SCHEMA "{schema}"')
            except (
                psycopg.errors.InsufficientPrivilege
            ):  # tài khoản test không được tạo schema (Neon): dùng `public`, xóa bảng khi xong
                schema = "public"
            conn.execute(
                f'CREATE TABLE "{schema}".customers (id BIGINT, email TEXT, phone TEXT, full_name TEXT, city TEXT)'
            )
            conn.execute(
                f'CREATE TABLE "{schema}".orders (order_id BIGINT, customer_email TEXT, total DOUBLE PRECISION, status TEXT)'
            )
            with conn.cursor() as cursor:
                cursor.executemany(f'INSERT INTO "{schema}".customers VALUES (%s, %s, %s, %s, %s)', CUSTOMERS)
                cursor.executemany(f'INSERT INTO "{schema}".orders VALUES (%s, %s, %s, %s)', ORDERS)
        monkeypatch.setenv(secrets.env_name("conn_test_pg"), make_conninfo(dsn, options=f"-c search_path={schema}"))
        ref = "conn_test_pg"
        default_tables = ["customers", "orders"]  # `public` còn có bảng của ứng dụng: chỉ cho hai bảng thử

        def drop() -> None:
            with psycopg.connect(dsn, autocommit=True) as conn:
                if schema == "public":
                    conn.execute("DROP TABLE IF EXISTS public.customers, public.orders")
                else:
                    conn.execute(f'DROP SCHEMA "{schema}" CASCADE')

        cleanup.append(drop)

    def build(**overrides) -> object:
        overrides.setdefault("allowed_tables", default_tables)
        return get_connector(make_source(kind, ref, **overrides))

    yield build
    for action in cleanup:
        action()


def set_option(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    get_settings.cache_clear()


# ---------- Bộ test hợp đồng: cùng giao diện, cùng kết quả mong đợi ----------


@pytest.mark.parametrize("backend", BACKENDS, indirect=True)
class TestContract:
    def test_lists_only_allowed_tables(self, backend):
        assert sorted(backend().list_tables()) == ["customers", "orders"]
        assert backend(allowed_tables=["orders"]).list_tables() == ["orders"]

    def test_disallowed_table_looks_like_missing_table(self, backend):
        limited = backend(allowed_tables=["orders"])
        for connector_call in (limited.get_schema, limited.get_profile, limited.require_table):
            with pytest.raises(TableNotAllowedError) as hidden:
                connector_call("customers")
            with pytest.raises(TableNotAllowedError) as missing:
                connector_call("bang_khong_ton_tai")
            assert str(hidden.value) == str(missing.value) == NOT_ALLOWED  # không lộ bảng có tồn tại hay không

    def test_schema_and_fingerprint(self, backend):
        connector = backend()
        assert list(connector.get_schema("orders").columns) == ["order_id", "customer_email", "total", "status"]
        first, again = connector.get_schema_fingerprint(), connector.get_schema_fingerprint()
        assert first.digest == again.digest and set(first.tables) == {"customers", "orders"}
        assert set(first.tables["orders"].values()) <= {
            "integer",
            "decimal",
            "float",
            "string",
            "boolean",
            "date",
            "timestamp",
            "json",
            "other",
        }
        only_orders = connector.get_schema_fingerprint(["orders"])
        assert set(only_orders.tables) == {"orders"} and only_orders.digest != first.digest

    def test_profile_has_counts_and_shapes_but_no_real_values_for_sensitive_columns(self, backend):
        connector = backend()
        profile = connector.get_profile("customers")
        assert profile.rows == 6 and profile.columns["city"]["distinct"] == 2
        for name in ("email", "phone", "full_name"):
            info = profile.columns[name]
            assert info["sensitive"] is True and info["shapes"] and not ({"min", "max", "top_values"} & set(info))
        assert all(secret not in json.dumps(profile.model_dump(), ensure_ascii=False) for secret in CANARIES)
        assert "top_values" not in profile.columns["city"]  # nguồn medium: không liệt kê giá trị phổ biến
        orders = connector.get_profile("orders")
        assert orders.rows == 10 and orders.columns["status"]["distinct"] == 3

    @pytest.mark.parametrize(
        ("sensitivity", "access"), [("medium", "profile"), ("high", "schema_only"), ("low", "profile")]
    )
    def test_sample_refused_unless_masked_sample(self, backend, sensitivity: str, access: str):
        with pytest.raises(SampleNotAllowedError):
            backend(sensitivity=sensitivity, llm_access=access).sample("customers", 3)

    def test_sample_is_masked_and_capped(self, backend):
        rows = backend(sensitivity="low", llm_access="masked_sample").sample("customers", 100)
        assert len(rows) == get_settings().llm_sample_max_rows == 5
        assert all(
            secret not in json.dumps(rows, ensure_ascii=False) for secret in CANARIES
        )  # cột nhạy cảm chỉ còn dạng giá trị
        assert rows[0]["city"] in ("Hà Nội", "HCM")  # cột không nhạy cảm đi qua pii.py
        assert backend(sensitivity="low", llm_access="masked_sample").sample("customers", 0) == []

    def test_load_to_sandbox_returns_counts_only(self, backend, tmp_path):
        with duckdb.connect(str(tmp_path / "sandbox.duckdb")) as con:
            counts = backend().load_to_sandbox(["customers", "orders"], con, 1000)
            assert counts == {"customers": 6, "orders": 10}
            assert con.execute("SELECT count(*) FROM raw.orders").fetchone()[0] == 10
            assert (
                con.execute("SELECT count(*) FROM raw.customers WHERE email LIKE 'canary.%'").fetchone()[0] == 6
            )  # medium: giữ nguyên

    def test_row_cap_gives_a_repeatable_subset(self, backend, tmp_path):
        picks = []
        for run in range(2):
            with duckdb.connect(str(tmp_path / f"sandbox{run}.duckdb")) as con:
                counts = backend().load_to_sandbox(["orders"], con, 4)
                assert counts == {"orders": 4}
                picks.append(sorted(r[0] for r in con.execute("SELECT order_id FROM raw.orders").fetchall()))
        assert picks[0] == picks[1]  # hạt giống cố định: cùng giới hạn → cùng tập con

    def test_high_sensitivity_hashes_sensitive_columns_consistently_so_joins_still_match(self, backend, tmp_path):
        with duckdb.connect(str(tmp_path / "sandbox.duckdb")) as con:
            backend(sensitivity="high", llm_access="schema_only").load_to_sandbox(["customers", "orders"], con, 1000)
            hashed = [r[0] for r in con.execute("SELECT email FROM raw.customers ORDER BY id").fetchall()]
            assert all(v.startswith("h_") and len(v) == 18 for v in hashed) and len(set(hashed)) == 6
            assert (
                con.execute(
                    "SELECT count(*) FROM raw.customers WHERE phone LIKE '09%' OR full_name LIKE '%Canary%'"
                ).fetchone()[0]
                == 0
            )
            joined = con.execute(
                "SELECT count(*) FROM raw.orders o JOIN raw.customers c ON c.email = o.customer_email"
            ).fetchone()[0]
            assert joined == 10  # băm có muối, nhất quán giữa hai bảng: JOIN theo cột nhạy cảm vẫn khớp
            assert (
                con.execute("SELECT count(*) FROM raw.customers WHERE city IN ('Hà Nội', 'HCM')").fetchone()[0] == 6
            )  # cột thường giữ

    def test_hash_switch_always_and_never(self, backend, tmp_path, monkeypatch):
        set_option(monkeypatch, "SANDBOX_HASH_SENSITIVE", "always")
        try:
            with duckdb.connect(str(tmp_path / "a.duckdb")) as con:
                backend(sensitivity="low").load_to_sandbox(["customers"], con, 1000)
                assert con.execute("SELECT count(*) FROM raw.customers WHERE email LIKE 'h_%'").fetchone()[0] == 6
            set_option(monkeypatch, "SANDBOX_HASH_SENSITIVE", "never")
            with duckdb.connect(str(tmp_path / "b.duckdb")) as con:
                backend(sensitivity="high", llm_access="schema_only").load_to_sandbox(["customers"], con, 1000)
                assert con.execute("SELECT count(*) FROM raw.customers WHERE email LIKE 'canary.%'").fetchone()[0] == 6
        finally:
            monkeypatch.undo()
            get_settings.cache_clear()

    def test_restricted_columns_are_hashed_too(self, backend, tmp_path):
        with duckdb.connect(str(tmp_path / "sandbox.duckdb")) as con:
            backend(sensitivity="high", llm_access="schema_only", restricted_columns=["city"]).load_to_sandbox(
                ["customers"], con, 1000
            )
            assert con.execute("SELECT count(*) FROM raw.customers WHERE city LIKE 'h_%'").fetchone()[0] == 6

    def test_cannot_load_a_disallowed_table(self, backend, tmp_path):
        with duckdb.connect(str(tmp_path / "sandbox.duckdb")) as con, pytest.raises(TableNotAllowedError):
            backend(allowed_tables=["orders"]).load_to_sandbox(["customers"], con, 1000)

    def test_health_check_and_catalog(self, backend):
        connector = backend()
        health = connector.health_check()
        assert health.ok and "2 bảng" in health.message
        catalog = connector.catalog()
        assert {c["name"] for c in catalog} == {"customers", "orders"}
        assert all(c["sample"] == [] and "email" in c["columns"] or c["name"] == "orders" for c in catalog)


# ---------- Khác biệt riêng của từng bộ nạp ----------


def test_file_connector_keeps_old_ingest_behaviour(tmp_path, monkeypatch):
    """Nạp qua khung chung cho cùng bảng raw như `ingest_sources` cũ (CSV giữ nguyên chuỗi)."""
    from src.agents.tools.duckdb_tools import discover_sources, ingest_sources

    _write_csv(tmp_path / "files")
    monkeypatch.setenv(secrets.env_name("conn_keep_old"), str(tmp_path / "files"))
    with duckdb.connect(str(tmp_path / "new.duckdb")) as con:
        get_connector(make_source("file", "conn_keep_old")).load_to_sandbox(["customers", "orders"], con, 1000)
        new = {t: con.execute(f"SELECT * FROM raw.{t} ORDER BY 1").fetchall() for t in ("customers", "orders")}
    ingest_sources(tmp_path / "old.duckdb", discover_sources(tmp_path / "files"))
    with duckdb.connect(str(tmp_path / "old.duckdb")) as con:
        old = {t: con.execute(f"SELECT * FROM raw.{t} ORDER BY 1").fetchall() for t in ("customers", "orders")}
    assert new == old


def test_connector_health_reports_missing_secret_and_folder_in_vietnamese(tmp_path, monkeypatch):
    health = get_connector(make_source("file", "conn_chua_dat_bi_mat")).health_check()
    assert not health.ok and "P113_SECRET_CONN_CHUA_DAT_BI_MAT" in health.message
    monkeypatch.setenv(secrets.env_name("conn_thu_muc_sai"), str(tmp_path / "khong-co"))
    assert not get_connector(make_source("file", "conn_thu_muc_sai")).health_check().ok


def test_duckdb_connector_opens_read_only(tmp_path, monkeypatch):
    _write_duckdb(tmp_path / "ro.duckdb")
    monkeypatch.setenv(secrets.env_name("conn_ro"), str(tmp_path / "ro.duckdb"))
    connector = get_connector(make_source("duckdb", "conn_ro"))
    with connector._read() as con, pytest.raises(duckdb.Error):
        con.execute("DELETE FROM orders")
    assert connector.get_profile("orders").rows == 10  # nguồn không bị đổi
    assert not get_connector(make_source("duckdb", "conn_ro_khong_co")).health_check().ok


def test_duckdb_connector_requires_secret_ref_in_registry_and_reports_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv(secrets.env_name("conn_missing_file"), str(tmp_path / "khong-co.duckdb"))
    health = get_connector(make_source("duckdb", "conn_missing_file")).health_check()
    assert not health.ok and "không tồn tại" in health.message


# ---------- Kiểu chuẩn hóa ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BIGINT", "integer"), ("integer", "integer"), ("int8", "integer"), ("DECIMAL(18,3)", "decimal"), ("numeric", "decimal"),
        ("DOUBLE", "float"), ("double precision", "float"), ("real", "float"), ("VARCHAR", "string"), ("character varying(20)", "string"),
        ("text", "string"), ("BOOLEAN", "boolean"), ("DATE", "date"), ("TIMESTAMP", "timestamp"),
        ("timestamp with time zone", "timestamp"), ("TIMESTAMP WITH TIME ZONE", "timestamp"), ("jsonb", "json"),
        ("INTEGER[]", "other"), ("ARRAY", "other"), ("interval", "other"), ("", "other"),
    ],
)  # fmt: skip
def test_normalize_type(raw: str, expected: str):
    assert normalize_type(raw) == expected


def test_fingerprint_changes_when_a_column_type_changes(tmp_path, monkeypatch):
    _write_duckdb(tmp_path / "fp.duckdb")
    monkeypatch.setenv(secrets.env_name("conn_fp"), str(tmp_path / "fp.duckdb"))
    before = get_connector(make_source("duckdb", "conn_fp")).get_schema_fingerprint()
    with duckdb.connect(str(tmp_path / "fp.duckdb")) as con:
        con.execute("ALTER TABLE orders ALTER total SET DATA TYPE VARCHAR")
    after = get_connector(make_source("duckdb", "conn_fp")).get_schema_fingerprint()
    assert (
        before.digest != after.digest
        and before.tables["orders"]["total"] == "float"
        and after.tables["orders"]["total"] == "string"
    )


# ---------- PostgreSQL: chỉ đọc, bảng được phép (kiểm TRƯỚC khi tới cơ sở dữ liệu) ----------

ALLOWED = [
    "SELECT * FROM orders",
    "select o.order_id, c.city from orders o join customers c on c.email = o.customer_email where o.total > 10",
    "WITH big AS (SELECT * FROM orders WHERE total > 5) SELECT count(*) FROM big",
    "SELECT order_id FROM orders UNION ALL SELECT id FROM customers",
    "SELECT * FROM orders TABLESAMPLE BERNOULLI (10) REPEATABLE (42) LIMIT 5",
    "SELECT current_schema()",
]
REJECTED = [
    "INSERT INTO orders VALUES (1, 'a', 1, 'x')",
    "UPDATE orders SET status = 'x'",
    "DELETE FROM orders",
    "DROP TABLE orders",
    "TRUNCATE orders",
    "CREATE TABLE t (a int)",
    "ALTER TABLE orders ADD COLUMN x int",
    "GRANT ALL ON orders TO public",
    "COPY orders TO '/tmp/x.csv'",
    "SELECT * INTO new_table FROM orders",
    "SELECT * FROM orders FOR UPDATE",
    "SELECT 1; DROP TABLE orders",
    "SELECT nextval('seq')",
    "SELECT pg_sleep(100)",
    "WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d",
    "SELECT * FROM dblink('host=x', 'select 1') AS t(a int)",
    "chuỗi không phải SQL",
    "",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_check_select_accepts_plain_reads(sql: str):
    check_select(sql)


@pytest.mark.parametrize("sql", REJECTED)
def test_check_select_rejects_everything_that_is_not_a_plain_select(sql: str):
    with pytest.raises(ReadOnlyViolationError, match="SELECT"):
        check_select(sql)


def test_check_select_enforces_allowed_tables_including_qualified_and_ctes():
    allowed = {"orders", "public.customers"}
    check_select("SELECT * FROM orders", allowed)
    check_select("SELECT * FROM public.customers", allowed)
    check_select("WITH x AS (SELECT * FROM orders) SELECT * FROM x", allowed)  # tên CTE không phải bảng ngoài quyền
    for sql in (
        "SELECT * FROM secrets",
        "SELECT * FROM orders JOIN payroll ON true",
        "SELECT * FROM other.customers",
        "WITH x AS (SELECT * FROM payroll) SELECT * FROM x",
        "SELECT * FROM orders WHERE id IN (SELECT id FROM payroll)",
    ):
        with pytest.raises(ReadOnlyViolationError, match="ngoài danh sách được phép"):
            check_select(sql, allowed)


class _NeverTouched:
    """Kết nối giả: mọi lần chạm tới đều là lỗi — chứng minh câu lệnh bị chặn TRƯỚC khi tới cơ sở dữ liệu."""

    touched = 0

    def __enter__(self):
        _NeverTouched.touched += 1
        raise AssertionError("câu lệnh lẽ ra phải bị chặn trước khi mở kết nối")

    def __exit__(self, *args):
        return False


@pytest.mark.parametrize(
    "sql", ["INSERT INTO orders VALUES (1)", "UPDATE orders SET a = 1", "DELETE FROM orders", "DROP TABLE orders"]
)
def test_postgres_connector_rejects_writes_before_reaching_the_database(sql: str):
    _NeverTouched.touched = 0
    connector = PostgresConnector(make_source("postgres", "conn_x", allowed_tables=["orders"]), connect=_NeverTouched)
    with pytest.raises(ReadOnlyViolationError):
        connector._select(sql)
    assert _NeverTouched.touched == 0


def test_postgres_connector_rejects_tables_outside_allowed_tables_before_reaching_the_database():
    _NeverTouched.touched = 0
    connector = PostgresConnector(make_source("postgres", "conn_x", allowed_tables=["orders"]), connect=_NeverTouched)
    with pytest.raises(ReadOnlyViolationError, match="ngoài danh sách"):
        connector._select("SELECT * FROM customers")
    assert _NeverTouched.touched == 0


def test_postgres_connection_failure_message_never_contains_the_password(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        secrets.env_name("conn_pg_down"), "postgresql://p113_reader:MAT-KHAU-RIENG-12345@127.0.0.1:1/p113_retail"
    )
    set_option(monkeypatch, "CONNECTOR_TIMEOUT_SEC", "1")
    try:
        health = get_connector(make_source("postgres", "conn_pg_down")).health_check()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
    assert not health.ok and "PostgreSQL" in health.message and "MAT-KHAU-RIENG-12345" not in health.message


def test_postgres_missing_secret_gives_vietnamese_message():
    health = get_connector(make_source("postgres", "conn_pg_chua_dat")).health_check()
    assert not health.ok and "P113_SECRET_CONN_PG_CHUA_DAT" in health.message


@pytest.mark.skipif(not RUN_PG, reason="cần RUN_PG_TESTS=1")
class TestPostgresReal:
    """Chỉ chạy với PostgreSQL thật: phiên chỉ đọc kể cả với tài khoản có quyền ghi."""

    @pytest.mark.parametrize("backend", ["postgres"], indirect=True)
    def test_session_is_read_only_even_for_a_privileged_account(self, backend):
        import psycopg

        connector = backend()
        schema = connector._load_tables()["customers"]["schema"]
        with connector._connect() as conn, pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute(f'DELETE FROM "{schema}".customers')

    @pytest.mark.parametrize("backend", ["postgres"], indirect=True)
    def test_data_survives_every_attempt(self, backend):
        connector = backend()
        for sql in ("DELETE FROM customers", "DROP TABLE customers", "UPDATE customers SET city = 'x'"):
            with pytest.raises(ReadOnlyViolationError):
                connector._select(sql)
        assert connector.get_profile("customers").rows == 6

    @pytest.mark.parametrize("backend", ["postgres"], indirect=True)
    def test_catalog_uses_search_path_schema_for_bare_names(self, backend):
        names = {item["name"] for item in backend().catalog()}
        assert names == {"customers", "orders"} and all(item["kind"] == "postgres" for item in backend().catalog())

    def test_unreachable_database_error_is_connector_error(self, monkeypatch):
        monkeypatch.setenv(secrets.env_name("conn_pg_nope"), "postgresql://u:p@127.0.0.1:1/x")
        with pytest.raises(ConnectorError):
            get_connector(make_source("postgres", "conn_pg_nope")).list_tables()


# ---------- Chạy trọn luồng qua từng bộ nạp: kết quả giống hệt luồng tệp ----------


def _complete_run(username: str) -> dict:
    """Chạy luồng mock tới bước duyệt (trả lời J1 bằng lựa chọn đầu, đồng ý kế hoạch); trả state cuối."""
    from src.agents import runner
    from src.agents.runner import ResumeRequest

    outcome = runner.start_run("Gộp đơn hàng 3 nguồn, tính doanh thu ngày", username)
    answers = {q["id"]: q["options"][0] for q in outcome.pending["questions"]}
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="clarify", value={"answers": answers}))
    assert outcome.status == "waiting_plan_review", (
        outcome.status,
        outcome.error,
        runner.get_values(outcome.run_id).get("spec_errors"),
    )
    outcome = runner.resume_run(ResumeRequest(run_id=outcome.run_id, kind="plan", value={"decision": "approve"}))
    assert outcome.status == "waiting_review", outcome.error
    return runner.get_values(outcome.run_id)


def _register_user_with_source(kind: str, secret_ref: str, tables: list[str]) -> str:
    import secrets as pysecrets

    from src.models.sources import CreateSourceBody
    from src.services import auth
    from src.services import source_registry as registry

    suffix = uuid.uuid4().hex[:6]
    department = registry.create_department(f"phong-e2e-{suffix}")
    registry.create_source(
        CreateSourceBody(
            name=f"e2e-{suffix}", department_id=department.id, kind=kind, secret_ref=secret_ref,
            allowed_tables=tables, sensitivity="medium",
        ),
        "adm",
    )  # fmt: skip
    username = f"e2e-{suffix}"
    auth.create_user(username, username, "engineer", pysecrets.token_urlsafe(16), department.id)
    return username


@pytest.mark.slow
def test_full_run_through_duckdb_connector_matches_file_run(seeded_sources: Path, tmp_path, monkeypatch):
    from src.agents.tools.duckdb_tools import discover_sources, load_sources

    path = tmp_path / "retail.duckdb"
    with duckdb.connect(str(path)) as con:
        load_sources(con, discover_sources(seeded_sources))
        for table in ("shopee_orders", "tiki_orders", "website_orders"):
            con.execute(f"CREATE TABLE main.{table} AS SELECT * FROM raw.{table}")
        con.execute("DROP SCHEMA raw CASCADE")
    monkeypatch.setenv(secrets.env_name("conn_e2e_duck"), str(path))
    names = ["shopee_orders", "tiki_orders", "website_orders"]
    through_duckdb = _complete_run(_register_user_with_source("duckdb", "conn_e2e_duck", names))
    through_files = _complete_run("an-qua-tep")  # người dùng phòng mặc định: nguồn P113 Retail (tệp)
    assert through_duckdb["row_counts"] == through_files["row_counts"]
    assert (
        through_duckdb["sandbox"]["passed"]
        and through_duckdb["sandbox"]["sample"] == through_files["sandbox"]["sample"]
    )
    assert {i["source_kind"] for i in through_duckdb["source_catalog"]} == {"duckdb"}


@pytest.mark.skipif(not RUN_PG, reason="cần RUN_PG_TESTS=1")
@pytest.mark.slow
def test_full_run_through_postgres_connector_matches_file_run(seeded_sources: Path, monkeypatch):
    """Ca demo chạy qua PostgresConnector: nạp 3 nguồn mẫu vào PostgreSQL, chạy luồng, kết quả giống luồng tệp."""
    import importlib.util

    import psycopg
    from psycopg.conninfo import make_conninfo

    from src.agents.tools.duckdb_tools import discover_sources

    spec = importlib.util.spec_from_file_location(
        "seed_pg_sources", Path(__file__).resolve().parent.parent / "scripts" / "seed_pg_sources.py"
    )
    seeder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seeder)  # type: ignore[union-attr]
    dsn = _pg_dsn().replace("postgresql+psycopg://", "postgresql://", 1)
    names = ["shopee_orders", "tiki_orders", "website_orders"]
    seeder.seed_schema(dsn, "public", discover_sources(seeded_sources), names)
    try:
        monkeypatch.setenv(secrets.env_name("conn_e2e_pg"), make_conninfo(dsn, options="-c search_path=public"))
        through_pg = _complete_run(_register_user_with_source("postgres", "conn_e2e_pg", names))
        through_files = _complete_run("an-qua-tep-pg")
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute("DROP TABLE IF EXISTS public.shopee_orders, public.tiki_orders, public.website_orders")
    assert through_pg["row_counts"] == through_files["row_counts"]
    assert through_pg["sandbox"]["passed"] and through_pg["sandbox"]["sample"] == through_files["sandbox"]["sample"]
    assert {i["source_kind"] for i in through_pg["source_catalog"]} == {"postgres"}


@pytest.mark.parametrize("bad_file", ["private_payroll.json", "private_payroll.sqlite"])
def test_file_connector_skips_disallowed_malformed_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_file: str):
    (tmp_path / "orders.csv").write_text("order_id,amount\nA-1,125000\n", encoding="utf-8")
    (tmp_path / bad_file).write_text("{ invalid data", encoding="utf-8")
    monkeypatch.setenv(secrets.env_name("conn_extract_scope"), str(tmp_path))
    source = make_source("file", "conn_extract_scope", allowed_tables=["orders"])
    connector = get_connector(source)
    assert connector.list_tables() == ["orders"]
    with duckdb.connect() as con:
        assert connector.load_to_sandbox(["orders"], con, 10) == {"orders": 1}
        assert con.execute("select order_id, amount from raw.orders").fetchall() == [("A-1", "125000")]


def test_file_connector_filters_sqlite_tables_before_reading_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import sqlite3

    from src.agents.tools import duckdb_tools

    with sqlite3.connect(tmp_path / "source.sqlite") as con:
        con.execute("create table orders (id integer)")
        con.execute("insert into orders values (1)")
        con.execute("create table private_payroll (id integer)")
    read = duckdb_tools._sqlite_rows
    visited = []

    def checked(path, table, limit=None):
        visited.append(table)
        assert table == "orders", "Bảng ngoài quyền không được đọc dòng mẫu"
        return read(path, table, limit)

    monkeypatch.setattr(duckdb_tools, "_sqlite_rows", checked)
    monkeypatch.setenv(secrets.env_name("conn_extract_scope"), str(tmp_path))
    connector = get_connector(make_source("file", "conn_extract_scope", allowed_tables=["source_orders"]))
    assert connector.list_tables() == ["source_orders"]
    assert visited == ["orders"]
