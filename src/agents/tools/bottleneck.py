"""Báo cáo điểm nghẽn (V, code thuần, 0 token): xếp model theo thời gian dbt đo, `EXPLAIN ANALYZE` top N trên sandbox.

Chỉ dùng số đo của lần `dbt build` đã chạy (không chạy thêm dbt). Bằng chứng chỉ gồm tên toán tử, thời gian, số dòng: không có
hằng số hay dòng dữ liệu. Lỗi hoặc hết thời gian → "chưa phân tích được", không làm hỏng pipeline.
"""

import time
from pathlib import Path

import duckdb

from src.agents.tools.dbt_tools import read_archived_run
from src.agents.tools.duckdb_tools import explain_plan
from src.agents.tools.slow_patterns import detect_slow_patterns
from src.models.evidence import Bottleneck, PerfReport

UNKNOWN = "Đo trên sandbox DuckDB với dữ liệu thử; chưa biết hành vi trên dữ liệu và kho thật."
# Tiền tố tên toán tử DuckDB → (giả thuyết, bước kiểm tra tiếp)
HYPOTHESES = {
    ("NESTED_LOOP_JOIN", "PIECEWISE_MERGE_JOIN", "BLOCKWISE_NL_JOIN", "CROSS_PRODUCT"): (
        "Nối không theo điều kiện bằng (khoảng, bất đẳng thức) hoặc tích Đề-các.",
        "Xem điều kiện nối; thử nối bằng khóa rồi lọc khoảng, so kết quả bằng V3.",
    ),
    ("HASH_JOIN",): (
        "Phép nối lớn: khóa nối có thể nhân dòng, hoặc lọc đặt sau nối.",
        "Đếm số dòng mỗi khóa nối ở hai phía; thử lọc trước khi nối rồi so kết quả bằng V3.",
    ),
    ("HASH_GROUP_BY", "PERFECT_HASH_GROUP_BY", "DISTINCT"): (
        "Gom nhóm trên nhiều dòng: có thể DISTINCT thừa hoặc gom trước khi lọc.",
        "Kiểm tra số dòng vào/ra của bước gom; bỏ DISTINCT thừa nếu khóa đã duy nhất.",
    ),
    ("WINDOW", "STREAMING_WINDOW"): (
        "Hàm cửa sổ phải phân vùng và sắp xếp toàn bộ dữ liệu.",
        "Xem có thay được bằng gom nhóm hoặc lọc trước khi tính cửa sổ.",
    ),
    ("ORDER_BY", "TOP_N"): (
        "Sắp xếp toàn bộ dữ liệu; ORDER BY trong truy vấn con thường thừa.",
        "Bỏ ORDER BY không ảnh hưởng kết quả cuối, so kết quả bằng V3.",
    ),
    ("SEQ_SCAN", "TABLE_SCAN", "READ_"): (
        "Đọc toàn bảng: có thể chọn thừa cột hoặc điều kiện lọc chưa đẩy xuống.",
        "Chỉ chọn cột cần dùng; kiểm tra điều kiện lọc có nằm ở bước đọc không.",
    ),
}


def _operators(node: dict) -> list[dict]:
    found = [] if node.get("operator_type") in (None, "EXPLAIN_ANALYZE") else [node]
    for child in node.get("children", []):
        found += _operators(child)
    return found


def _hypothesis(operator: str) -> tuple[str, str]:
    for prefixes, answer in HYPOTHESES.items():
        if operator.startswith(prefixes):
            return answer
    return "Chưa có giả thuyết riêng cho toán tử này.", "Xem kế hoạch thực thi đầy đủ của model."


def _finding(rank: int, timing: dict, total_ms: float, plan: dict, sql: str) -> Bottleneck:
    ops = _operators(plan)
    hot = max(ops, key=lambda n: n.get("operator_timing", 0), default={})
    name = str(hot.get("operator_name", "?")).strip()
    op_total = sum(n.get("operator_timing", 0) for n in ops) or 1.0
    child_rows = [c.get("operator_cardinality", 0) for c in hot.get("children", [])]
    evidence = [
        f"Toán tử {name} chiếm {100 * hot.get('operator_timing', 0) / op_total:.0f}% thời gian toán tử "
        f"({hot.get('operator_timing', 0) * 1000:.1f} ms), ra {hot.get('operator_cardinality', 0)} dòng"
        + (f" từ đầu vào {child_rows} dòng" if child_rows else "")
    ]
    try:
        evidence += [f"Dấu hiệu tĩnh ({f.rule}): {f.message}" for f in detect_slow_patterns(sql)]
    except Exception:  # noqa: BLE001, S110 — dấu hiệu tĩnh chỉ là phụ
        pass
    hypothesis, next_step = _hypothesis(name)
    share = 100 * timing["execute_ms"] / total_ms if total_ms else 0
    return Bottleneck(
        model=timing["model"],
        rank=rank,
        execute_ms=timing["execute_ms"],
        operator=name,
        phenomenon=f"Model {timing['model']} chạy {timing['execute_ms']:.1f} ms, {share:.0f}% tổng thời gian các model.",
        evidence=evidence,
        hypothesis=hypothesis,
        next_step=next_step,
        unknown=UNKNOWN,
    )


def analyze_bottlenecks(workspace: Path, db: Path, sandbox: dict, top_n: int, budget_sec: float) -> PerfReport:
    """Xếp model theo `execute_ms`, phân tích tối đa `top_n` model trong `budget_sec` giây."""
    measured = [t for t in sandbox.get("model_timings") or [] if t.get("execute_ms") is not None]
    if not measured:
        return PerfReport(note="Chưa đo: lần chạy không có số đo từng model.")
    ranked = sorted(measured, key=lambda t: t["execute_ms"], reverse=True)
    total = round(sum(t["execute_ms"] for t in measured), 3)
    archived = read_archived_run(workspace, sandbox.get("dbt_invocation", ""))
    sql_of = {r["unique_id"].rsplit(".", 1)[-1]: r.get("sql", "") for r in archived.get("results", [])}
    start, findings = time.perf_counter(), []
    for rank, timing in enumerate(ranked[:top_n], 1):
        remaining = budget_sec - (time.perf_counter() - start)
        reason = "" if sql_of.get(timing["model"]) else "Chưa phân tích được: không còn SQL đã biên dịch của model."
        reason = reason or ("" if remaining > 0 else "Chưa phân tích được: hết thời gian phân tích.")
        if not reason:
            try:
                plan = explain_plan(db, sql_of[timing["model"]], timeout_sec=remaining)
                findings.append(_finding(rank, timing, total, plan, sql_of[timing["model"]]))
                continue
            except (duckdb.Error, ValueError, IndexError) as exc:
                reason = f"Chưa phân tích được: {type(exc).__name__}."
        findings.append(
            Bottleneck(
                model=timing["model"], rank=rank, execute_ms=timing["execute_ms"], analyzed=False, unknown=reason
            )
        )
    return PerfReport(
        measured=True,
        model_total_ms=total,
        pipeline_wall_ms=sandbox.get("wall_ms"),
        analysis_ms=round((time.perf_counter() - start) * 1000, 3),
        top_n=top_n,
        findings=findings,
    )
