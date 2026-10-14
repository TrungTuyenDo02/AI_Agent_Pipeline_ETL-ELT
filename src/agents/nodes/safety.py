"""V1 An toàn (code thuần, 0 token): kiểm tra mọi file sinh ra trước khi chạy trong sandbox.

- SQL: chỉ một câu SELECT; chặn DROP/ATTACH/INSTALL/COPY/PRAGMA/SET, hàm đọc file, đường dẫn tuyệt đối, Jinja lạ.
- Mọi bảng/cột phải có trong danh mục thật (sqlglot qualify); DuckDB biên dịch thử (EXPLAIN, chỉ đọc) từng model.
- DAG: biên dịch được, có DAG(...), có thứ tự task, không ghi cứng thông tin kết nối.
"""

import ast
import re
from pathlib import Path

from src.agents.nodes.common import all_files, mart_path, register_failure, sandbox_db, spec_of
from src.agents.nodes.testgen import cast_tests
from src.agents.state import PipelineState
from src.agents.tools.dbt_tools import is_allowed_path
from src.agents.tools.duckdb_tools import explain_error, read_catalog
from src.agents.tools.sql_tools import (
    SqlCheckError,
    expand_models,
    explain_column_error,
    find_unknown_tables,
    find_unsafe_constructs,
    inline_refs,
    output_columns,
    parse_single_select,
    readable_columns,
    render_dbt_sql,
    select_star_issues,
)
from src.config import get_settings
from src.models.contracts import SafetyResult, hand_off

Catalog = dict[str, dict[str, dict[str, str]]]
SECRET_RE = re.compile(r"password\s*=|passwd|secret\s*=|api[_-]?key\s*=|(postgres|mysql|snowflake)://\S+:\S+@", re.I)


def check_sql(sql: str, catalog: Catalog) -> tuple[list[str], list[str]]:
    """Kiểm tra một file SQL; trả về (lỗi, cột đầu ra). Jinja lạ/config() sai → lỗi (không ném ngoại lệ)."""
    try:
        rendered = render_dbt_sql(sql)
        tree = parse_single_select(rendered)
    except SqlCheckError as exc:
        return [str(exc)], []
    issues = find_unsafe_constructs(tree) + find_unknown_tables(tree, catalog)
    if issues:
        return issues, []
    try:
        return [], output_columns(tree, catalog)
    except SqlCheckError as exc:
        return [explain_column_error(str(exc), rendered, readable_columns(tree, catalog, str(exc)))], []


PREFLIGHT_TASK = "check_source_schema"


def _leftmost(node: ast.AST) -> ast.AST:
    while isinstance(node, ast.BinOp) and isinstance(node.op, ast.RShift):
        node = node.left
    return node


def _preflight_issues(tree: ast.AST) -> list[str]:
    """DAG phải bắt đầu bằng task chạy macro `check_source_schema` (preflight) trước mọi task biến đổi: chuỗi `>>` ngoài cùng
    phải mở đầu bằng biến của task đó."""
    tasks = {
        target.id: node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    def is_preflight(leaf: ast.AST) -> bool:
        call = tasks.get(leaf.id) if isinstance(leaf, ast.Name) else None
        texts = (
            [c.value for c in ast.walk(call) if isinstance(c, ast.Constant) and isinstance(c.value, str)]
            if call
            else []
        )
        return any(PREFLIGHT_TASK in text for text in texts)

    chains = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.RShift)]
    inner = {id(n.left) for n in chains if isinstance(n.left, ast.BinOp) and isinstance(n.left.op, ast.RShift)}
    outer = [n for n in chains if id(n) not in inner]
    if any(is_preflight(_leftmost(n)) for n in outer):
        return []
    return [
        f"DAG phải có task đầu tiên chạy `dbt run-operation {PREFLIGHT_TASK}` (kiểm cấu trúc nguồn) trước mọi task biến đổi, "
        f"ví dụ: preflight >> build_models >> run_tests."
    ]


def check_dag(source: str) -> list[str]:
    """Kiểm tra DAG Airflow bằng AST (không cần cài Airflow)."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"DAG lỗi cú pháp Python dòng {exc.lineno}: {exc.msg}"]
    calls = {getattr(n.func, "id", getattr(n.func, "attr", "")) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    issues = [] if "DAG" in calls else ["DAG không có lời gọi DAG(...)."]
    tasks = sum(1 for n in ast.walk(tree) if isinstance(n, ast.keyword) and n.arg == "task_id")
    has_order = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.RShift) for n in ast.walk(tree))
    if tasks > 1 and not has_order:
        issues.append("DAG có nhiều task nhưng chưa khai báo thứ tự (toán tử >>).")
    if SECRET_RE.search(source):
        issues.append("DAG có vẻ ghi cứng mật khẩu/chuỗi kết nối — dùng Airflow Connection/Variable.")
    preflight = _preflight_issues(tree) if "DAG" in calls else []
    return issues + preflight + dangerous_dag_code(tree)


# Airflow chạy code cấp module của DAG mỗi lần đọc file: chặn lệnh hệ thống, mạng, chạy code động, đọc file
BLOCKED_DAG_MODULES = {
    "subprocess", "socket", "ctypes", "pty", "requests", "urllib", "httpx", "paramiko", "importlib", "builtins",
}  # fmt: skip
BLOCKED_DAG_CALLS = {"eval", "exec", "compile", "__import__", "getattr", "open"}
# Hàm của module được phép import (os, shutil) nhưng là thao tác hệ thống; so khớp cả tên gốc lẫn tiền tố exec*/spawn*
BLOCKED_DAG_ATTRS = {
    "os": {"system", "popen", "remove", "unlink", "rmdir", "removedirs", "rename", "replace", "kill", "killpg",
           "fork", "chmod", "chown", "putenv"},
    "shutil": {"rmtree", "move", "copy", "copyfile", "copytree", "chown"},
}  # fmt: skip
BLOCKED_ATTR_PREFIXES = {"os": ("exec", "spawn", "posix_spawn")}
# Chuỗi trong DAG (trừ docstring) chỉ để chạy dbt: không tải/chạy script từ mạng, không xóa đệ quy, không chạy python -c
BASH_DANGER_RE = re.compile(r"\|\s*(ba|z)?sh\b|\bcurl\b|\bwget\b|\brm\s+-[a-z]*r|\bnc\b|\bchmod\b|\bpython3?\s+-c\b")


def _blocked_attr(module: str, attr: str) -> bool:
    return attr in BLOCKED_DAG_ATTRS.get(module, set()) or attr.startswith(BLOCKED_ATTR_PREFIXES.get(module, ("\0",)))


def _import_aliases(tree: ast.AST) -> tuple[dict[str, str], list[str]]:
    """(tên cục bộ → module, lỗi): `import os as o` → o=os; `from os import system` bị chặn ngay khi import."""
    aliases: dict[str, str] = {}
    issues: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                aliases[alias.asname or root] = root
                if root in BLOCKED_DAG_MODULES:
                    issues.append(f"DAG không được import '{root}' (lệnh hệ thống/mạng/code động).")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in BLOCKED_DAG_MODULES:
                issues.append(f"DAG không được import '{root}' (lệnh hệ thống/mạng/code động).")
            issues.extend(
                f"DAG không được dùng {root}.{alias.name} (thao tác hệ thống)."
                for alias in node.names
                if _blocked_attr(root, alias.name)
            )
    return aliases, issues


def _docstrings(tree: ast.AST) -> set[int]:
    """id() của các hằng chuỗi là docstring (module/hàm/lớp) — không coi là lệnh."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def dangerous_dag_code(tree: ast.AST) -> list[str]:
    """Lệnh hệ thống/mạng/code động trong DAG (kể cả qua bí danh import), và chuỗi lệnh shell nguy hiểm."""
    aliases, issues = _import_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in BLOCKED_DAG_CALLS:
            issues.append(f"DAG không được gọi {func.id}() (chạy code động hoặc đọc file).")
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            module = aliases.get(func.value.id, func.value.id)
            if _blocked_attr(module, func.attr):
                issues.append(f"DAG không được gọi {module}.{func.attr}() (thao tác hệ thống).")
    docstrings = _docstrings(tree)
    texts = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
    ]
    if any(BASH_DANGER_RE.search(text) for text in texts):
        issues.append(
            "Lệnh trong DAG chỉ được chạy dbt; phát hiện tải/chạy script, xóa đệ quy, đổi quyền hoặc python -c."
        )
    return list(dict.fromkeys(issues))


def _model_name(path: str) -> str:
    return path.rsplit("/", 1)[-1].removesuffix(".sql")


def check_models(sql_files: dict[str, str], catalog: Catalog) -> tuple[list[str], dict[str, list[str]]]:
    """Kiểm tra model theo thứ tự phụ thuộc; model đã đạt được thêm vào danh mục `main`."""
    issues: list[str] = []
    outputs: dict[str, list[str]] = {}
    pending = dict(sql_files)
    while pending:
        progressed = False
        for path, sql in list(pending.items()):
            errors, columns = check_sql(sql, catalog)
            if errors and any("không có trong danh mục" in e for e in errors) and len(pending) > 1:
                continue
            if path.startswith(("models/staging/", "models/marts/")):
                errors = errors + select_star_issues(sql)
            pending.pop(path)
            progressed = True
            issues.extend(f"{path}: {e}" for e in errors)
            outputs[path] = columns
            if columns:
                catalog.setdefault("main", {})[_model_name(path)] = {c: "VARCHAR" for c in columns}
        if not progressed:
            path, sql = pending.popitem()
            issues.extend(f"{path}: {e}" for e in check_sql(sql, catalog)[0])
    return issues, outputs


def _structure_issues(state: PipelineState, files: dict[str, str]) -> list[str]:
    spec = spec_of(state)
    issues = [f"Đường dẫn file không được phép: {p}" for p in files if not is_allowed_path(p)]
    if mart_path(spec) not in files:
        issues.append(f"Thiếu model đích {mart_path(spec)}.")
    if not any(p.startswith("dags/") for p in files):
        issues.append("Thiếu DAG Airflow trong thư mục dags/.")
    return issues


def _mart_columns_issue(state: PipelineState, outputs: dict[str, list[str]]) -> list[str]:
    spec = spec_of(state)
    expected, actual = [c.name for c in spec.output_columns], outputs.get(mart_path(spec))
    # Tên cột DuckDB không phân biệt hoa/thường (sqlglot trả về chữ thường); model lỗi (rỗng) đã báo ở lỗi gốc
    if actual and {a.lower() for a in actual} != {e.lower() for e in expected}:
        missing = sorted({e.lower() for e in expected} - {a.lower() for a in actual})
        extra = sorted({a.lower() for a in actual} - {e.lower() for e in expected})
        return [f"Cột của model đích khác đặc tả: thiếu {missing}, thừa {extra}."]
    return []


def drop_cascading(issues: list[str], outputs: dict[str, list[str]]) -> list[str]:
    """Bỏ lỗi dây chuyền "bảng main.X không có" khi chính model X đã lỗi, để Coder thấy đúng lỗi gốc."""
    failed = {_model_name(path) for path, columns in outputs.items() if not columns}
    kept = [i for i in issues if not any(f"'main.{name}' không có" in i for name in failed)]
    return kept or issues  # không bao giờ để rỗng khi thực tế có lỗi (ví dụ tham chiếu vòng)


def compile_issues(sql_files: dict[str, str], db: Path) -> list[str]:
    """Biên dịch thử model + test bằng DuckDB EXPLAIN (chỉ đọc, 0 token) để lỗi hàm/kiểu gắn ĐÚNG file.

    Không có bước này, lỗi trong staging ephemeral bị dbt báo ở model đích nên Coder sửa nhầm chỗ.
    """
    rendered = {path: render_dbt_sql(sql) for path, sql in sql_files.items()}
    models = expand_models({_model_name(p): sql for p, sql in rendered.items() if p.startswith("models/")})
    errors: dict[str, str] = {}
    for path, sql in rendered.items():
        full = inline_refs(sql, models)
        if not re.search(r"\bmain\.", full) and (error := explain_error(db, full)):
            errors[path] = error
    failed = {_model_name(path) for path in errors if path.startswith("models/")}
    return [
        f"{path}: DuckDB không biên dịch được: {error}"
        for path, error in errors.items()
        if not any(re.search(rf"\bmain\.{name}\b", rendered[path]) for name in failed)
    ]  # bỏ lỗi dây chuyền ở file gọi tới model đã lỗi


def _defensive_test_issues(state: PipelineState, files: dict[str, str]) -> list[str]:
    """Phòng thủ chống đổi cấu trúc: mỗi cột nguồn đọc bằng biểu thức ép kiểu phải có test đếm dòng không ép được (ngưỡng
    CAST_FAIL_THRESHOLD). Thiếu = ép kiểu thất bại có thể âm thầm thành rỗng mà không ai biết."""
    expected = cast_tests(state.get("profile", {}), get_settings().cast_fail_threshold)
    return [f"Thiếu test ép kiểu bắt buộc: {path}." for path in expected if path not in files]


def run_safety_checks(state: PipelineState) -> list[str]:
    """Toàn bộ kiểm tra V1 cho code + test hiện tại."""
    files = all_files(state)
    issues = _structure_issues(state, files)
    catalog = {k: v for k, v in read_catalog(sandbox_db(state)).items() if k == "raw"}
    models = {p: s for p, s in files.items() if p.startswith("models/") and p.endswith(".sql")}
    model_issues, outputs = check_models(models, catalog)
    tests = {p: s for p, s in files.items() if p.startswith("tests/") and p.endswith(".sql")}
    test_issues = [f"{p}: {e}" for p, s in tests.items() for e in check_sql(s, catalog)[0]]
    dag_issues = [f"{p}: {e}" for p, s in files.items() if p.startswith("dags/") for e in check_dag(s)]
    defensive = _defensive_test_issues(state, files)
    all_issues = issues + model_issues + test_issues + dag_issues + _mart_columns_issue(state, outputs) + defensive
    if all_issues:
        return drop_cascading(all_issues, outputs)
    return compile_issues({**models, **tests}, sandbox_db(state))


def safety_node(state: PipelineState) -> dict:
    """Chặn code không an toàn/bịa tên; lỗi được ghi sổ lỗi và đếm vào vòng sửa."""
    issues = run_safety_checks(state)
    result: dict = {"safety": hand_off(SafetyResult, {"passed": not issues, "issues": issues})}
    if issues:
        result.update(
            register_failure(
                state, "\n".join(issues), sql_before=state.get("code_files", {}).get(mart_path(spec_of(state)), "")
            )
        )
    return result
