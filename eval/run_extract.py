"""Eval Extract bằng file/oracle độc lập: python eval/run_extract.py (không LLM, không mạng)."""

import argparse
import copy
import hashlib
import json
import os
import secrets as random_secrets
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from extract_score import compare_snapshot, row_bag, summarize  # noqa: E402

DATASET = ROOT / "eval" / "datasets" / "extract_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def materialize(dataset: Path, work: Path) -> Path:
    """Tạo DB/Parquet thật từ blueprint đã đóng băng; không sinh đáp án từ kết quả connector."""
    home = work / "sources"
    shutil.copytree(dataset / "sources", home)
    (home / "sqlite").mkdir()
    (home / "parquet").mkdir()
    tables = json.loads((dataset / "native_tables.json").read_text(encoding="utf-8"))["tables"]
    with (
        duckdb.connect(str(home / "warehouse.duckdb")) as con,
        closing(sqlite3.connect(home / "sqlite" / "warehouse.sqlite")) as sql,
    ):
        for table in tables:
            schema, name, columns = table["schema"], table["name"], table["columns"]
            if any(dtype not in {"BIGINT", "VARCHAR"} for _, dtype in columns):
                raise ValueError("Blueprint eval chỉ nhận BIGINT/VARCHAR; không chạy SQL kiểu tùy ý")
            con.execute(f"CREATE SCHEMA IF NOT EXISTS {quote(schema)}")
            definition = ", ".join(f"{quote(c)} {t}" for c, t in columns)
            con.execute(f"CREATE TABLE {quote(schema)}.{quote(name)} ({definition})")
            placeholders = ", ".join("?" for _ in columns)
            if table["rows"]:
                con.executemany(f"INSERT INTO {quote(schema)}.{quote(name)} VALUES ({placeholders})", table["rows"])
            if schema == "main":
                definition = ", ".join(f"{quote(c)} {'INTEGER' if t == 'BIGINT' else 'TEXT'}" for c, t in columns)
                sql.execute(f"CREATE TABLE {quote(name)} ({definition})")
                sql.executemany(f"INSERT INTO {quote(name)} VALUES ({placeholders})", table["rows"])
        sql.commit()
        parquet = str(home / "parquet" / "orders.parquet").replace("'", "''")
        con.execute(f"COPY main.orders TO '{parquet}' (FORMAT PARQUET)")
    return home


def isolate(work: Path) -> None:
    """Chỉ CLI gọi, trong tiến trình riêng: không kết nối DB hoặc secret của dev/prod."""
    url = f"sqlite+pysqlite:///{(work / 'registry.db').as_posix()}"
    os.environ.update(
        {
            "DATABASE_URL": url,
            "MIGRATION_DATABASE_URL": url,
            "APP_ENV": "test",
            "SOURCES_DIR": str(work / "fallback_not_source"),
            "WORKSPACES_DIR": str(work / "workspaces"),
            "STATE_BACKEND": "sqlite",
            "STORE_PATH": str(work / "app.db"),
            "CHECKPOINT_PATH": str(work / "checkpoints.db"),
            "SESSION_SECRET": random_secrets.token_urlsafe(48),
            "SECRETS_DIR": str(work / "empty_secrets"),
            "LLM_PROVIDER": "mock",
            "LLM_FALLBACK": "none",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "LANGCHAIN_TRACING_V2": "false",
            "LANGSMITH_TRACING": "false",
            "SANDBOX_LOAD_MAX_ROWS": "100",
            "SANDBOX_HASH_SENSITIVE": "auto",
            "SANDBOX_HASH_SALT": "extract-eval-only",
        }
    )


class ExtractBench:
    def __init__(self, dataset: Path, work: Path):
        from alembic import command
        from alembic.config import Config

        from src.config import get_settings
        from src.models.sources import CreateSourceBody
        from src.services import auth, secrets, source_registry

        get_settings.cache_clear()
        self.dataset, self.work = dataset, work
        self.manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
        self.expected = json.loads((dataset / "expected.json").read_text(encoding="utf-8"))
        self.home = materialize(dataset, work)
        self.initial_hashes = self.source_hashes()
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "migrations"))
        config.set_main_option("sqlalchemy.url", get_settings().database_url)
        command.upgrade(config, "head")
        departments = {key: source_registry.create_department(f"Extract eval {key}") for key in ("sales", "finance")}
        self.users = {}
        for key, department in departments.items():
            name = f"extract_{key}"
            auth.create_user(name, name, "engineer", random_secrets.token_urlsafe(24) + "Aa1!", department.id)
            self.users[key] = name
        self.sources = {}
        for item in self.manifest["sources"]:
            ref = f"extract_eval_{item['key']}"
            location = (self.home / item["location"]).resolve()
            if not location.is_relative_to(self.home.resolve()):
                raise ValueError("Nguồn eval phải nằm trong thư mục dữ liệu tạm")
            os.environ[secrets.env_name(ref)] = str(location)
            self.sources[item["key"]] = source_registry.create_source(
                CreateSourceBody(
                    name=f"Extract {item['key']}",
                    department_id=departments[item["department"]].id,
                    kind=item["kind"],
                    secret_ref=ref,
                    allowed_tables=item["allowed_tables"],
                    sensitivity="low",
                ),
                "extract-eval",
            )
        self.results = []

    def source_hashes(self) -> dict:
        return {p.relative_to(self.home).as_posix(): sha256(p) for p in sorted(self.home.rglob("*")) if p.is_file()}

    def record(self, case_id: str, category: str, run, critical: bool = False) -> None:
        started = time.perf_counter()
        try:
            result = run()
            result["passed"] = bool(result.get("checks")) and all(result["checks"].values())
        except Exception as exc:  # noqa: BLE001 — ghi lỗi thành điểm trượt, CLI trả mã 1; không lộ giá trị dữ liệu
            result = {"passed": False, "error_type": type(exc).__name__}
        self.results.append(
            {
                "id": case_id,
                "category": category,
                "critical": critical,
                "seconds": round(time.perf_counter() - started, 4),
                **result,
            }
        )
        print(f"{'PASS' if result['passed'] else 'FAIL'} {case_id}", flush=True)

    def extract(self, key: str, table: str, oracle: dict, max_rows: int = 100) -> dict:
        from src.agents.nodes.ingest import _load
        from src.config import get_settings
        from src.services import source_registry
        from src.services.connectors import get_connector

        source = self.sources[key]
        department = next(s["department"] for s in self.manifest["sources"] if s["key"] == key)
        actor = self.users[department]
        catalog = source_registry.visible_catalog(source_registry.user_context(actor), source_ids=[source.id])
        items = [i for i in catalog if i["name"] == table]
        if len(items) != 1:
            raise ValueError("Nguồn hoặc bảng không được phân giải duy nhất")
        physical = Path(items[0]["path"]) if items[0].get("path") else get_connector(source).path()
        before = sha256(physical)
        db = self.work / f"load_{len(list(self.work.glob('load_*.duckdb')))}.duckdb"
        settings = get_settings()
        old_max = settings.sandbox_load_max_rows
        settings.sandbox_load_max_rows = max_rows
        try:
            counts = _load(items, str(db), {"requester": actor})
        finally:
            settings.sandbox_load_max_rows = old_max
        with duckdb.connect(str(db), read_only=True) as con:
            result = con.execute(f"SELECT * FROM raw.{quote(table)}")
            actual = {"schema": [[c[0], str(c[1])] for c in result.description], "rows": result.fetchall()}
            loaded = [
                r[0]
                for r in con.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='raw'"
                ).fetchall()
            ]
        score = compare_snapshot(oracle, actual)
        if max_rows < len(oracle["rows"]):
            score["checks"] = {
                "schema_exact": oracle["schema"] == actual["schema"],
                "row_cap": len(actual["rows"]) == max_rows,
                "subset_with_duplicates": not (row_bag(actual["rows"]) - row_bag(oracle["rows"])),
            }
        score["checks"] |= {
            "source_id_exact": items[0]["source_id"] == source.id,
            "only_requested_table": loaded == [table],
            "count_matches_sandbox": counts == {table: len(actual["rows"])},
            "source_bytes_unchanged": before == sha256(physical),
        }
        score["receipt"] = {
            "source_id": source.id,
            "source_name": source.name,
            "department": department,
            "connector": type(get_connector(source)).__name__,
            "table": table,
            "artifact": physical.relative_to(self.home).as_posix(),
            "input_sha256": before,
            "schema": actual["schema"],
            "loaded_rows": len(actual["rows"]),
            "max_rows": max_rows,
        }
        return score

    def denied(self, key: str, actor: str) -> dict:
        from src.agents.nodes.ingest import _load
        from src.services.connectors import ConnectorError

        denied = False
        db = self.work / "denied.duckdb"
        try:
            _load([{"name": "orders", "source_id": self.sources[key].id}], str(db), {"requester": actor})
        except ConnectorError:
            denied = True
        with duckdb.connect(str(db)) as con:
            count = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='raw'").fetchone()[0]
        return {"checks": {"request_denied": denied, "no_table_loaded": count == 0}}

    def run(self) -> dict:
        from src.models.sources import UpdateSourceBody
        from src.services import source_registry
        from src.services.connectors import TableNotAllowedError, get_connector
        from src.services.secrets import SecretError, env_name

        for case in self.manifest["cases"]:
            self.record(
                case["id"],
                "exact_extract",
                lambda c=case: self.extract(c["source"], c["table"], self.expected[c["oracle"]]),
            )

        def sampling():
            a = self.extract("sales", "orders", self.expected["sales_orders"], 3)
            b = self.extract("sales", "orders", self.expected["sales_orders"], 3)
            a["checks"]["repeatable"] = a["actual_digest"] == b["actual_digest"]
            a["checks"]["second_load_valid"] = all(b["checks"].values())
            return a

        def forbidden():
            denied = False
            with duckdb.connect() as con:
                try:
                    get_connector(self.sources["sales"]).load_to_sandbox(["private_payroll"], con, 100)
                except TableNotAllowedError:
                    denied = True
                count = con.execute(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='raw'"
                ).fetchone()[0]
            return {"checks": {"forbidden_table_denied": denied, "no_forbidden_table_loaded": count == 0}}

        def visibility():
            visible = {
                s.id for s in source_registry.get_visible_sources(source_registry.user_context(self.users["sales"]))
            }
            expected = {self.sources[s["key"]].id for s in self.manifest["sources"] if s["department"] == "sales"}
            return {"checks": {"departments_isolated": visible == expected}}

        def revoked():
            source = self.sources["sales"]
            source_registry.update_source(source.id, UpdateSourceBody(enabled=False), "extract-eval")
            try:
                return self.denied("sales", self.users["sales"])
            finally:
                source_registry.update_source(source.id, UpdateSourceBody(enabled=True), "extract-eval")

        def changed_input():
            path = self.home / "partner_sales" / "orders.csv"
            original = path.read_bytes()
            initial = self.extract("sales", "orders", self.expected["sales_orders"])
            try:
                path.write_bytes(original.replace(b"125000", b"125001", 1))
                oracle = copy.deepcopy(self.expected["sales_orders"])
                oracle["rows"][0][3] = "125001"
                changed = self.extract("sales", "orders", oracle)
                changed["checks"]["baseline_valid"] = all(initial["checks"].values())
                changed["checks"]["input_changed"] = (
                    initial["receipt"]["input_sha256"] != changed["receipt"]["input_sha256"]
                )
                changed["checks"]["output_changed"] = initial["actual_digest"] != changed["actual_digest"]
                return changed
            finally:
                path.write_bytes(original)

        def privacy():
            source = self.sources["duckdb"]
            private = source.model_copy(
                update={
                    "sensitivity": "high",
                    "llm_access": "schema_only",
                    "restricted_columns": ["email", "customer_email"],
                }
            )
            with duckdb.connect() as con:
                get_connector(private).load_to_sandbox(["orders", "customers"], con, 100)
                emails = [r[0] for r in con.execute("SELECT email FROM raw.customers ORDER BY id").fetchall()]
                expected = [
                    "h_" + hashlib.sha256(("extract-eval-only" + email).encode()).hexdigest()[:16]
                    for email in ("mai@example.invalid", "an@example.invalid")
                ]
                joined = con.execute(
                    "SELECT count(*) FROM raw.orders o JOIN raw.customers c ON o.customer_email=c.email"
                ).fetchone()[0]
                nulls = con.execute("SELECT count(*) FROM raw.orders WHERE customer_email IS NULL").fetchone()[0]
            return {
                "checks": {
                    "independent_hash_matches": emails == expected,
                    "join_preserved": joined == 3,
                    "null_preserved": nulls == 1,
                }
            }

        def missing_secret():
            source = self.sources["sales"].model_copy(update={"secret_ref": "extract_eval_missing"})
            os.environ.pop(env_name(source.secret_ref), None)
            denied = False
            try:
                get_connector(source).list_tables()
            except SecretError:
                denied = True
            return {"checks": {"missing_secret_does_not_fall_back": denied}}

        def controls():
            wanted = self.expected["sales_orders"]
            wrong_source = compare_snapshot(wanted, self.expected["finance_orders"])
            missing_duplicate = copy.deepcopy(wanted)
            missing_duplicate["rows"][3] = list(missing_duplicate["rows"][0])
            renamed = copy.deepcopy(wanted)
            renamed["schema"][0][0] = "wrong_id"
            reordered = copy.deepcopy(wanted)
            reordered["rows"].reverse()
            return {
                "checks": {
                    "wrong_source_rejected": not wrong_source["passed"],
                    "wrong_duplicate_count_rejected": not compare_snapshot(wanted, missing_duplicate)["passed"],
                    "wrong_schema_rejected": not compare_snapshot(wanted, renamed)["passed"],
                    "row_order_accepted": compare_snapshot(wanted, reordered)["passed"],
                }
            }

        self.record("sampling_repeatable_subset", "sampling", sampling)
        self.record("forbidden_table", "access", forbidden, True)
        self.record("department_visibility", "access", visibility, True)
        self.record("cross_department_ingest", "access", lambda: self.denied("finance", self.users["sales"]), True)
        self.record("revoked_source_ingest", "access", revoked, True)
        self.record("changed_file_changes_output", "provenance", changed_input, True)
        self.record("hashed_join", "privacy", privacy, True)
        self.record("missing_secret", "access", missing_secret, True)
        self.record(
            "source_immutability",
            "provenance",
            lambda: {"checks": {"all_source_bytes_unchanged": self.initial_hashes == self.source_hashes()}},
            True,
        )
        self.record("scorer_negative_controls", "scorer", controls, True)
        return {
            "dataset_id": self.manifest["dataset_id"],
            "origin": self.manifest["origin"],
            "manifest_sha256": sha256(self.dataset / "manifest.json"),
            "oracle_sha256": sha256(self.dataset / "expected.json"),
            "fixture_sha256": {
                p.relative_to(self.dataset).as_posix(): sha256(p)
                for p in sorted(self.dataset.rglob("*"))
                if p.is_file()
            },
            "measured_at": datetime.now(UTC).isoformat(),
            "scope": ["CSV", "JSON", "SQLite", "DuckDB", "Parquet"],
            "not_evaluated": [
                "PostgreSQL thật",
                "kiểu native phức tạp và múi giờ",
                "API đối tác",
                "CDC/incremental",
                "lựa chọn nguồn tự động khi trùng tên bảng",
            ],
            "llm_calls": 0,
            "summary": summarize(self.results),
            "cases": self.results,
        }


def write_results(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "extract.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = report["summary"]
    lines = [
        "# Đánh giá Extract",
        "",
        f"- Dataset: `{report['dataset_id']}`; dữ liệu tổng hợp, oracle cố định độc lập.",
        f"- Đạt **{summary['passed']}/{summary['total']}** ({summary['pass_rate_pct']}%); nghiệm thu: **{'đạt' if summary['accepted'] else 'chưa đạt'}**.",
        "- Gọi connector, sổ nguồn và hàm nạp thật trong tiến trình/SQLite tạm riêng; 0 LLM, không mạng.",
        f"- Thời gian harness gồm dựng fixture và kiểm tra: {report['duration_sec']} giây; không đại diện độ trễ sản phẩm.",
        "- Điểm chỉ cho phạm vi đã chạy; mọi ca phải qua, lỗi quyền/nguồn không được bù bằng điểm khác.",
        "- Chưa đánh giá: " + ", ".join(report["not_evaluated"]) + ".",
        "",
        "| Ca | Nhóm | Đạt | Thời gian (s) |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| `{r['id']}` | {r['category']} | {'đạt' if r['passed'] else 'trượt'} | {r['seconds']} |"
        for r in report["cases"]
    ]
    lines += [
        "",
        "## Bằng chứng nguồn",
        "",
        "Mã băm của file nguồn đã vật chất hóa, source_id và bảng được chọn; không ghi DSN, đường dẫn bí mật hoặc dòng dữ liệu vào báo cáo.",
        "Mã băm xác nhận nội dung trong lần eval này; không phải chữ ký xác nhận nguồn ngoài thực tế.",
        "",
        "| Ca | Source ID | Connector | File được đọc | Bảng | Dòng nạp | SHA-256 đầu vào |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| `{r['id']}` | {p['source_id']} | {p['connector']} | `{p['artifact']}` | `{p['table']}` | {p['loaded_rows']} | `{p['input_sha256']}` |"
        for r in report["cases"]
        if (p := r.get("receipt"))
    ]
    lines += [
        "",
        "Chi tiết schema, digest kết quả thực tế/đáp án và các phép kiểm tra nằm trong [extract.json](extract.json).",
        "",
        "Ca `changed_file_changes_output` sửa bản sao đầu vào và đòi hỏi đầu ra đổi tương ứng; ca `scorer_negative_controls` kiểm tra sai nguồn cùng số dòng, sai dòng trùng và sai schema đều bị chấm trượt.",
        "CSV giữ nguyên chuỗi ở raw (kể cả số 0 đầu, tiền dạng chuỗi); benchmark này chấm Extract, không chấm làm sạch hay khả năng suy luận của LLM.",
    ]
    (output / "extract.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval" / "results")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="p113-extract-eval-") as directory:
        work = Path(directory)
        isolate(work)
        bench = ExtractBench(args.dataset.resolve(), work)
        report = bench.run()
        report["duration_sec"] = round(time.perf_counter() - started, 4)
        write_results(report, args.output_dir)
        from src.services.auth import get_engine

        get_engine().dispose()
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["summary"]["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
