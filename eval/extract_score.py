"""Chấm Extract bằng oracle cố định; không phụ thuộc connector hay code sinh pipeline."""

import hashlib
import json
from collections import Counter


def row_bag(rows: list) -> Counter[str]:
    return Counter(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) for row in rows
    )


def snapshot_digest(snapshot: dict) -> str:
    payload = {"schema": snapshot["schema"], "rows": sorted(row_bag(snapshot["rows"]).items())}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def compare_snapshot(expected: dict, observed: dict) -> dict:
    wanted, actual = row_bag(expected["rows"]), row_bag(observed["rows"])
    checks = {
        "schema_exact": expected["schema"] == observed["schema"],
        "row_count_exact": len(expected["rows"]) == len(observed["rows"]),
        "rows_exact_with_duplicates": wanted == actual,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "expected_rows": len(expected["rows"]),
        "actual_rows": len(observed["rows"]),
        "differing_rows": (wanted - actual).total() + (actual - wanted).total(),
        "expected_digest": snapshot_digest(expected),
        "actual_digest": snapshot_digest(observed),
    }


def summarize(results: list[dict]) -> dict:
    passed = sum(r["passed"] for r in results)
    return {
        "passed": passed,
        "total": len(results),
        "pass_rate_pct": round(100 * passed / len(results), 2) if results else 0,
        "critical_failures": [r["id"] for r in results if r.get("critical") and not r["passed"]],
        "accepted": bool(results) and passed == len(results),
    }
