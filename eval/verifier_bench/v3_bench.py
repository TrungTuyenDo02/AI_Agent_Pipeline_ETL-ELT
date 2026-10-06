"""V3 như một máy dò: cặp query tương đương / "na ná", dữ liệu ngẫu nhiên, luật viết lại, bất biến (0 token).

- Phán quyết V3 = đúng `check_equivalence` của hệ thống trên 5 bộ dữ liệu thử do E2 sinh (small, dirty, empty, few,
  dupkeys) từ một kho raw mẫu.
- Dữ liệu ngẫu nhiên: N bộ nhỏ (seed cố định) có rỗng, trùng dòng, khóa mồ côi, giờ trùng, giây lẻ, chữ hoa/thường —
  dùng làm "bằng chứng độc lập": cặp `different` lệch ở ≥ 1 bộ là chắc chắn khác; cặp `equivalent` phải không lệch bộ nào.
"""

import math
import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from src.agents.nodes.compare import EQUIVALENCE_DATASETS, check_equivalence, compare_results  # noqa: E402
from src.agents.nodes.mock_data import DatasetJob, build_dataset, recipes_from_profile  # noqa: E402
from src.agents.nodes.profiler import profile_table  # noqa: E402
from src.agents.tools.duckdb_tools import QueryResult, connect_read, read_catalog, run_query  # noqa: E402
from src.agents.tools.rewrite_rules import rules_candidate, sqlglot_candidate  # noqa: E402
from src.config import get_settings  # noqa: E402

RANDOM_DATASETS = 120
RANDOM_SEED = 20261005
CUSTOMERS = ["C1", "C2", "C3", "C4", "C5", "C6"]
STATUSES = ["paid", "paid", "PAID", "refunded", "cancelled", None]
CITIES = ["HN", "HCM", "DN"]
START = datetime(2026, 9, 1)

DDL = (
    "CREATE SCHEMA IF NOT EXISTS raw;"
    "CREATE TABLE raw.orders (order_id VARCHAR, customer_id VARCHAR, status VARCHAR, amount DOUBLE, created_at TIMESTAMP);"
    "CREATE TABLE raw.customers (customer_id VARCHAR, city VARCHAR);"
)


def _timestamp(rng: random.Random) -> datetime:
    """Giờ có trùng nhau và có giây lẻ sát nửa đêm (bẫy biên ngày)."""
    day = START + timedelta(days=rng.randint(0, 2))
    pick = rng.random()
    if pick < 0.15:
        return day + timedelta(hours=23, minutes=59, seconds=59, milliseconds=500)
    if pick < 0.35:
        return day + timedelta(hours=12)  # giờ trùng
    return day + timedelta(seconds=rng.randint(0, 86_399))


def _amount(rng: random.Random) -> float | None:
    pick = rng.random()
    if pick < 0.15:
        return None
    if pick < 0.3:
        return 100.0  # giá trị trùng
    return round(rng.uniform(10, 500), rng.choice([0, 1, 2]))


def random_tables(rng: random.Random, max_orders: int, max_customers: int) -> tuple[list[tuple], list[tuple]]:
    """Bảng orders/customers ngẫu nhiên có đủ kiểu bẩn."""
    orders = []
    for _ in range(rng.randint(0, max_orders)):
        customer = rng.choice([*CUSTOMERS, "C9", None])  # C9: khách mồ côi, None: thiếu khách
        orders.append((f"O{rng.randint(1, 15)}", customer, rng.choice(STATUSES), _amount(rng), _timestamp(rng)))
    if orders and rng.random() < 0.4:
        orders.append(rng.choice(orders))  # trùng nguyên dòng
    customers = [(rng.choice([*CUSTOMERS, None]), rng.choice(CITIES)) for _ in range(rng.randint(0, max_customers))]
    return orders, customers


def write_db(path: Path, orders: list[tuple], customers: list[tuple]) -> Path:
    """Ghi hai bảng vào một file DuckDB mới."""
    path.unlink(missing_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute(DDL)
        if orders:
            con.executemany("INSERT INTO raw.orders VALUES (?, ?, ?, ?, ?)", orders)
        if customers:
            con.executemany("INSERT INTO raw.customers VALUES (?, ?)", customers)
    return path


def system_datasets(work: Path) -> dict[str, str]:
    """Kho raw mẫu (300 đơn) → hồ sơ (P) → 5 bộ dữ liệu thử đúng như E2 sinh cho V3."""
    base = write_db(work / "base.duckdb", *random_tables(random.Random(0), 300, 40))
    profile = {t: profile_table(base, t, cols) for t, cols in read_catalog(base)["raw"].items()}
    recipes = recipes_from_profile(profile)
    out = {}
    for name in EQUIVALENCE_DATASETS:
        target = work / f"sys_{name}.duckdb"
        build_dataset(DatasetJob(name=name, source_db=base, target=target), recipes)
        out[name] = str(target)
    return out


def random_datasets(work: Path) -> list[Path]:
    """RANDOM_DATASETS bộ nhỏ, seed cố định."""
    rng = random.Random(RANDOM_SEED)
    return [write_db(work / f"rand_{i:03d}.duckdb", *random_tables(rng, 25, 8)) for i in range(RANDOM_DATASETS)]


def _query(con: duckdb.DuckDBPyConnection, sql: str) -> QueryResult:
    """Như run_query nhưng dùng lại một kết nối (nhanh hơn nhiều khi chạy hàng nghìn query nhỏ)."""
    rel = con.sql(sql)
    return QueryResult(columns=rel.columns, types=[str(t) for t in rel.types], rows=rel.fetchall())


def _differs(a: str, b: str, con: duckdb.DuckDBPyConnection) -> bool | str:
    """True/False nếu chạy được; chuỗi lỗi nếu một bên lỗi. So bằng đúng compare_results của V3."""
    try:
        return not compare_results(_query(con, a), _query(con, b), get_settings().compare_abs_tol)[0]
    except duckdb.Error as exc:
        return f"lỗi: {str(exc).splitlines()[0][:80]}"


def _outcomes(pairs: list[tuple[str, str]], rand_sets: list[Path]) -> list[list[bool | str]]:
    """outcomes[i][j]: cặp i trên bộ ngẫu nhiên j."""
    out: list[list[bool | str]] = [[] for _ in pairs]
    for db in rand_sets:
        with connect_read(db) as con:
            for i, (a, b) in enumerate(pairs):
                out[i].append(_differs(a, b, con))
    return out


def run_pairs(pairs: list[dict], sys_sets: dict[str, str], rand_sets: list[Path]) -> list[dict]:
    """Mỗi cặp: phán quyết V3 + số bộ ngẫu nhiên lệch."""
    rows = []
    all_outcomes = _outcomes([(p["a"], p["b"]) for p in pairs], rand_sets)
    for pair, outcomes in zip(pairs, all_outcomes, strict=True):
        checks = check_equivalence(pair["a"], pair["b"], sys_sets)
        v3_pass = all(c.equal for c in checks)
        rows.append(
            {
                "id": pair["id"],
                "label": pair["label"],
                "labeled_by": pair.get("labeled_by", "author"),
                "trap": pair.get("trap", ""),
                "v3_pass": v3_pass,
                "v3_detail": next((f"{c.dataset}: {c.detail}" for c in checks if not c.equal), "giống hệt mọi bộ"),
                "random_diff": sum(o is True for o in outcomes),
                "random_errors": sum(isinstance(o, str) for o in outcomes),
            }
        )
    return rows


def _assumptions_hold(candidate, con: duckdb.DuckDBPyConnection) -> bool:
    return all(not a.check_sql or _query(con, a.check_sql).rows[0][0] == 0 for a in candidate.assumptions)


def run_rule_queries(queries: list[dict], rand_sets: list[Path], schema: dict) -> list[dict]:
    """Bản tối ưu do luật tất định / sqlglot sinh phải cho kết quả y hệt trên mọi bộ ngẫu nhiên thỏa giả định."""
    rows = []
    for query in queries:
        for build in (rules_candidate, sqlglot_candidate):
            candidate = build(query["sql"], schema)
            if candidate is None:
                continue
            compared = mismatched = 0
            for db in rand_sets:
                with connect_read(db) as con:
                    if not _assumptions_hold(candidate, con):
                        continue
                    compared += 1
                    mismatched += _differs(query["sql"], candidate.sql, con) is not False
            rows.append(
                {
                    "id": query["id"],
                    "source": candidate.source,
                    "applied": ", ".join(candidate.applied),
                    "compared": compared,
                    "mismatched": mismatched,
                }
            )
    return rows


def _variant(src: Path, mode: str) -> duckdb.DuckDBPyConnection:
    """Bản sao trong bộ nhớ: `shuffle` xáo thứ tự dòng (seed cố định), `double` nhân đôi mọi dòng."""
    con = duckdb.connect()
    con.execute(f"ATTACH '{src.as_posix()}' AS s (READ_ONLY)")
    con.execute("CREATE SCHEMA raw")
    con.execute("SELECT setseed(0.42)")
    for table in ("orders", "customers"):
        body = f"SELECT * FROM s.raw.{table}"
        sql = f"{body} ORDER BY random()" if mode == "shuffle" else f"{body} UNION ALL {body}"
        con.execute(f"CREATE TABLE raw.{table} AS {sql}")
    con.execute("DETACH s")
    return con


def _doubled_ok(base: QueryResult, doubled: QueryResult, columns: list[str]) -> bool:
    idx = [base.columns.index(c) for c in columns]
    keys = [i for i in range(len(base.columns)) if i not in idx]

    def index(result: QueryResult) -> dict:
        return {tuple(row[i] for i in keys): row for row in result.rows}

    a, b = index(base), index(doubled)
    if a.keys() != b.keys():
        return False
    for key, row in a.items():
        for i in idx:
            x, y = row[i], b[key][i]
            if (x is None) != (y is None) or (x is not None and not math.isclose(2 * float(x), float(y), rel_tol=1e-9)):
                return False
    return True


def _comparator_ok(result: QueryResult) -> bool:
    """V3 phải coi hai kết quả chỉ khác thứ tự dòng là giống, và lệch một giá trị là khác."""
    tol = get_settings().compare_abs_tol
    if not compare_results(result, result.model_copy(update={"rows": result.rows[::-1]}), tol)[0]:
        return False
    for r, row in enumerate(result.rows):
        for c, value in enumerate(row):
            if isinstance(value, int | float) and not isinstance(value, bool):
                changed = [list(x) for x in result.rows]
                changed[r][c] = value + 1
                return not compare_results(result, result.model_copy(update={"rows": changed}), tol)[0]
    return True


def run_invariants(invariants: list[dict], rand_sets: list[Path]) -> list[dict]:
    """Xáo dòng → không đổi; nhân đôi → cột cộng dồn gấp đôi; tự kiểm bộ so sánh của V3."""
    rows = []
    for inv in invariants:
        shuffle_bad = double_bad = comparator_bad = 0
        for db in rand_sets:
            base = run_query(db, inv["sql"])
            with _variant(db, "shuffle") as con:
                shuffled = _query(con, inv["sql"])
            with _variant(db, "double") as con:
                doubled = _query(con, inv["sql"])
            shuffle_bad += not compare_results(base, shuffled, get_settings().compare_abs_tol)[0]
            double_bad += not _doubled_ok(base, doubled, inv["doubles"])
            comparator_bad += not _comparator_ok(base)
        rows.append(
            {
                "id": inv["id"],
                "datasets": len(rand_sets),
                "shuffle_bad": shuffle_bad,
                "double_bad": double_bad,
                "comparator_bad": comparator_bad,
            }
        )
    return rows


def run_all(work: Path) -> dict:
    """Chạy toàn bộ phần V3."""
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    config = yaml.safe_load((HERE / "v3_pairs.yaml").read_text(encoding="utf-8"))
    sys_sets, rand_sets = system_datasets(work), random_datasets(work)
    schema = read_catalog(rand_sets[0])
    return {
        "pairs": run_pairs(config["pairs"], sys_sets, rand_sets),
        "rules": run_rule_queries(config["rule_queries"], rand_sets, schema),
        "invariants": run_invariants(config["invariants"], rand_sets),
        "random_datasets": len(rand_sets),
        "random_seed": RANDOM_SEED,
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = run_all(ROOT / "data" / "eval_work" / "verifier_v3")
    for row in result["pairs"]:
        ok = row["v3_pass"] == (row["label"] == "equivalent")
        print(
            f"{'✓' if ok else '✗'} {row['id']}: V3 {'qua' if row['v3_pass'] else 'chặn'}, "
            f"ngẫu nhiên lệch {row['random_diff']}/{result['random_datasets']} (lỗi {row['random_errors']}) — {row['v3_detail'][:90]}"
        )
    for row in result["rules"]:
        print("rule", row)
    for row in result["invariants"]:
        print("inv", row)
