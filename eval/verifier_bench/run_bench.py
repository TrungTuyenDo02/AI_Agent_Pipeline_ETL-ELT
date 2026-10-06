"""U3 — đo chính các bước V như máy dò: bỏ sót (code sai mà V cho qua) và báo nhầm (code đúng mà V chặn).

Toàn bộ bằng code, 0 token, không dùng LLM. Kết quả: eval/results/verifier_report.md (+ verifier_report.json).

    python eval/verifier_bench/run_bench.py            # đủ: V1, V2 (dbt thật), V3, bất biến, tự kiểm (~5–8 phút)
    python eval/verifier_bench/run_bench.py --quick    # bỏ V2 và tự kiểm (nhanh, ~2 phút)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import v2_bench  # noqa: E402,I001  — nạp trước: đặt thư mục tạm riêng cho kho/sổ lỗi/workspace
import v1_bench  # noqa: E402
import v3_bench  # noqa: E402
from sabotage import SABOTAGES  # noqa: E402

RESULTS = ROOT / "eval" / "results"
SELF_CHECK_TARGETS = {
    "v0": ["tests/test_verifiers/test_spec_check.py"],
    "v1": ["tests/test_verifiers/test_v1_redteam.py", "tests/test_verifiers/test_safety_and_sandbox.py"],
    "v2": ["tests/test_verifiers/test_safety_and_sandbox.py"],
    "v3": ["tests/test_optimizer/test_optimizer.py"],
}
# Lỗi tìm thấy NGOÀI bộ ca V1 khi dựng bộ đo này (ca V1 lọt đã sửa đọc từ trường found_leak trong yaml)
FIXED_DURING_BUILD = [
    ("2026-10-05", "V1", "Jinja lạ / config() sai làm check_sql ném ngoại lệ → node V1 vỡ thay vì đưa lỗi cho Coder sửa."),
    ("2026-10-05", "E4", "Luật self_union_to_distinct không thay được UNION ở gốc câu (áp 20 lần, SQL không đổi)."),
    ("2026-10-05", "V3", "Không có bộ dữ liệu nào có nhóm toàn giá trị rỗng → SUM ra NULL thay vì 0 lọt qua; "
     "thêm bộ `nullmoney` (cột tiền rỗng toàn bộ) vào E2/V3."),
]  # fmt: skip
MITIGATIONS = {
    "count_distinct_id": "Dữ liệu giả lập không có mã đơn trùng giữa các nguồn. Thêm vào seed; Reviewer xem cách đếm.",
    "join_left_to_inner": "Dữ liệu golden không có đơn hoàn tất thiếu dòng hàng. Chạy test đối soát cả trên bộ "
    "dirty/dupkeys của E2; Reviewer kiểm kiểu JOIN.",
    "add_distinct_count": "Không có hai đơn cùng ngày cùng tổng tiền. Thêm dữ liệu có giá trị trùng; Reviewer đọc diff.",
    "count_items_not_orders": "Mọi đơn hoàn tất đều có dòng hàng nên count(cột phải) = count(*). Như join_left_to_inner.",
    "recursive_cte_dos": "Lọt đã biết: V1 không phân tích điểm dừng của CTE đệ quy. V2 chặn bằng SANDBOX_TIMEOUT_SEC + "
    "memory_limit; Reviewer thấy lỗi quá thời gian.",
    "range_explosion_dos": "Lọt đã biết: V1 không ước lượng số dòng. V2 chặn bằng timeout + memory_limit.",
    "diff_trim_whitespace": "Dữ liệu thử (và dữ liệu ngẫu nhiên) không có chuỗi thừa khoảng trắng nên không đo được. "
    "Profiler (P) gợi ý `normalize` khi dữ liệu thật có biến thể; Reviewer kiểm TRIM khi bản tối ưu bỏ nó.",
    "revenue_type_bigint": "V không so kiểu cột đầu ra với spec (đối soát so số có sai số). Nên thêm kiểm kiểu ở V1 "
    "(DESCRIBE model đích so với output_columns.type); trong lúc chờ Reviewer xem cột kiểu.",
    "dedup_ignores_source": "Như count_distinct_id: dữ liệu giả lập không có mã đơn trùng giữa các nguồn.",
    "dedup_tiebreak_lost": "Bản ghi trùng trong dữ liệu thử giống nhau ở cột tiền nên giữ bản nào cũng ra cùng số; "
    "thêm dữ liệu trùng mà khác số tiền.",
    "dedup_keeps_null_amount": "Dữ liệu thử không có cặp trùng mà một bản thiếu tiền; thêm vào seed.",
    "drop_coalesce_zero": "Không có ngày nào mọi đơn đều thiếu tiền trong dữ liệu thật; bộ `nullmoney` chỉ dùng cho V3.",
    "diff_limit_order_ties": "Kết quả không xác định (LIMIT với ORDER BY có giá trị trùng): V3 chỉ chặn khi lần chạy lệch. "
    "Reviewer chặn mọi bản tối ưu chạm ORDER BY/LIMIT; dữ liệu ngẫu nhiên bắt được 9/120 bộ.",
}


def v1_summary(results: list[v1_bench.V1Result]) -> dict:
    """Số ca, bắt được, bỏ sót, báo nhầm của V1."""
    attacks = [r for r in results if r.case.label == "block"]
    valid = [r for r in results if r.case.label == "pass"]
    return {
        "attacks": len(attacks),
        "valid": len(valid),
        "caught": sum(r.blocked for r in attacks),
        "missed": [r.case.id for r in attacks if not r.blocked],
        "false_blocks": [r.case.id for r in valid if r.blocked],
        "crashes": [r.case.id for r in results if "NGOẠI LỆ" in r.detail],
        "found_leaks": [(str(r.case.found_leak), r.case.id, r.case.note) for r in attacks if r.case.found_leak],
        "external": sum(r.case.labeled_by == "external" for r in results),
        "ai_proxy": sum(r.case.labeled_by == "ai_proxy" for r in results),
    }


def v2_summary(base: dict) -> dict:
    """Đột biến thật bắt được / bỏ sót, đối chứng báo nhầm của một pipeline gốc."""
    rows = [r for r in base["rows"] if r["applied"]]
    real, controls = [r for r in rows if not r["equivalent"]], [r for r in rows if r["equivalent"]]
    return {
        "base": base["base"],
        "sanity": base["sanity"],
        "real": len(real),
        "controls": len(controls),
        "caught": sum(r["caught"] for r in real),
        "missed": [r["id"] for r in real if not r["caught"]],
        "false_alarms": [r["id"] for r in controls if r["caught"]],
        "not_applied": [r["id"] for r in base["rows"] if not r["applied"]],
    }


def v3_summary(v3: dict) -> dict:
    """Cặp query: bắt được / bỏ sót / báo nhầm; nhãn mâu thuẫn với dữ liệu ngẫu nhiên."""
    pairs = v3["pairs"]
    diff, equal = [p for p in pairs if p["label"] == "different"], [p for p in pairs if p["label"] == "equivalent"]
    return {
        "equivalent": len(equal),
        "different": len(diff),
        "caught": sum(not p["v3_pass"] for p in diff),
        "missed": [p["id"] for p in diff if p["v3_pass"]],
        "false_blocks": [p["id"] for p in equal if not p["v3_pass"]],
        "label_conflicts": [p["id"] for p in equal if p["random_diff"]]
        + [p["id"] for p in diff if not p["random_diff"]],
    }


def run_self_check() -> list[dict]:
    """Chạy test của từng V khi V còn nguyên (phải xanh) và khi V bị phá (phải đỏ)."""
    env = {**os.environ, "PYTHONPATH": str(HERE), "PYTHONIOENCODING": "utf-8"}
    base_cmd = [sys.executable, "-m", "pytest", "-q", "--no-cov", "-p", "no:cacheprovider", "-p", "sabotage"]
    rows = []
    for kind, targets in SELF_CHECK_TARGETS.items():
        counts = {}
        for label, extra in (("intact", {}), ("broken", {"P113_SABOTAGE": kind})):
            done = subprocess.run(
                [*base_cmd, *targets], cwd=ROOT, env={**env, **extra}, capture_output=True, text=True, encoding="utf-8"
            )
            tail = done.stdout.strip().splitlines()[-1].strip("= ") if done.stdout.strip() else done.stderr[-200:]
            failed = re.search(r"(\d+) failed", tail)
            counts[label] = {"failed": int(failed.group(1)) if failed else 0, "summary": tail}
        rows.append({"sabotage": kind, "what": SABOTAGES[kind], "targets": targets, **counts})
        print(
            f"tự kiểm {kind}: nguyên vẹn {counts['intact']['summary']} | bị phá {counts['broken']['summary']}",
            flush=True,
        )
    return rows


def _ids(items: list[str]) -> str:
    return ", ".join(f"`{i}`" for i in items) or "—"


def by_labeler(data: dict) -> list[dict]:
    """Tách kết quả theo người gán nhãn (author / ai_proxy / external) cho từng node."""
    rows = []
    for labeler in ("author", "ai_proxy", "external"):
        v1 = [r for r in data["v1_rows"] if r.get("labeled_by", "author") == labeler]
        v2 = [
            r
            for b in data.get("v2_raw", [])
            for r in b["rows"]
            if r["applied"] and r.get("labeled_by", "author") == labeler
        ]
        v3 = [p for p in data["v3_raw"]["pairs"] if p.get("labeled_by", "author") == labeler]
        groups = {
            "V1": [(r["label"] == "block", r["blocked"]) for r in v1],
            "V2": [(not r["equivalent"], r["caught"]) for r in v2],
            "V3": [(p["label"] == "different", not p["v3_pass"]) for p in v3],
        }
        for node, items in groups.items():
            if items:
                bad = [hit for should, hit in items if should]
                good = [hit for should, hit in items if not should]
                rows.append(
                    {"labeler": labeler, "node": node, "bad": len(bad), "caught": sum(bad), "good": len(good),
                     "false": sum(good)}
                )  # fmt: skip
    return rows


def render(data: dict) -> str:
    """Báo cáo markdown."""
    v1, v3 = data["v1"], data["v3"]
    lines = [
        "# Đo các bước V như máy dò (U3)",
        "",
        f"- Ngày chạy: {data['date']} • toàn bộ bằng code, **0 token**, không dùng LLM để chấm.",
        "- **Bỏ sót** = code sai mà V cho qua. **Báo nhầm** = code đúng mà V chặn.",
        "- Nhãn: `author` = người viết hệ thống; `ai_proxy` = Claude viết thay thành viên khi chưa có người ngoài nhóm "
        f"({v1['ai_proxy']} ca V1, cùng một người viết V nên **không độc lập** như `external`); "
        f"`external` = người ngoài nhóm: {v1['external']} ca.",
        "- Kết quả chỉ nói về **bộ ca đã có**; không có nghĩa V không bao giờ sai.",
        "",
        "## 1. Tóm tắt theo node",
        "",
        "| Node | Ca đúng (phải qua) | Ca sai (phải chặn) | Bắt được | Bỏ sót | Báo nhầm |",
        "|---|---:|---:|---:|---:|---:|",
        f"| V1 An toàn (red team + ca hợp lệ) | {v1['valid']} | {v1['attacks']} | {v1['caught']} | {len(v1['missed'])} "
        f"| {len(v1['false_blocks'])} |",
    ]
    for base in data.get("v2", []):
        lines.append(
            f"| V2 Sandbox — đột biến `{base['base']}` | {base['controls']} | {base['real']} | {base['caught']} "
            f"| {len(base['missed'])} | {len(base['false_alarms'])} |"
        )
    if not data.get("v2"):
        lines.append("| V2 Sandbox — đột biến | — | — | — | — | — (bỏ qua: chạy với `--quick`) |")
    lines += [
        f"| V3 Đối chiếu — cặp query | {v3['equivalent']} | {v3['different']} | {v3['caught']} | {len(v3['missed'])} "
        f"| {len(v3['false_blocks'])} |",
        "",
        f"V1 ném ngoại lệ thay vì báo lỗi gọn: {_ids(v1['crashes'])}.",
        "",
        "### Theo người gán nhãn",
        "",
        "| Nhãn | Node | Ca sai | Bắt được | Ca đúng | Báo nhầm |",
        "|---|---|---:|---:|---:|---:|",
        *[
            f"| {r['labeler']} | {r['node']} | {r['bad']} | {r['caught']} | {r['good']} | {r['false']} |"
            for r in by_labeler(data)
        ],
        "",
        "## 2. V3 chi tiết: cặp query trên 6 bộ dữ liệu thử của hệ thống và trên dữ liệu ngẫu nhiên",
        "",
        f"Dữ liệu ngẫu nhiên: {data['v3_raw']['random_datasets']} bộ nhỏ, seed {data['v3_raw']['random_seed']} "
        "(rỗng, trùng dòng, khách mồ côi, giờ trùng, giây lẻ 23:59:59.5, chữ hoa/thường). "
        "Cột cuối: số bộ ngẫu nhiên mà hai query cho kết quả khác.",
        "",
        "| Cặp | Nhãn | Bẫy | V3 | Lý do V3 | Lệch trên dữ liệu ngẫu nhiên |",
        "|---|---|---|---|---|---:|",
    ]
    for p in data["v3_raw"]["pairs"]:
        verdict = "qua" if p["v3_pass"] else "chặn"
        ok = "✓" if p["v3_pass"] == (p["label"] == "equivalent") else "✗"
        detail = p["v3_detail"].replace("|", "\\|")[:90]
        lines.append(
            f"| {p['id']} | {p['label']} | {p['trap']} | {ok} {verdict} | {detail} | "
            f"{p['random_diff']}/{data['v3_raw']['random_datasets']} |"
        )
    lines += [
        "",
        f"Nhãn mâu thuẫn với dữ liệu ngẫu nhiên (cặp `equivalent` mà lệch, hoặc `different` mà không bộ nào lệch): "
        f"{_ids(v3['label_conflicts'])}.",
        "",
        "## 3. Luật viết lại của Optimizer trên dữ liệu ngẫu nhiên",
        "",
        "Bản tối ưu do luật tất định / sqlglot sinh phải cho kết quả y hệt bản gốc trên mọi bộ thỏa giả định của luật.",
        "",
        "| Query | Nguồn | Luật | Số bộ so | Lệch |",
        "|---|---|---|---:|---:|",
        *[
            f"| {r['id']} | {r['source']} | {r['applied']} | {r['compared']} | {r['mismatched']} |"
            for r in data["v3_raw"]["rules"]
        ],
        "",
        "## 4. Bất biến",
        "",
        "| Query | Số bộ | Xáo thứ tự dòng làm đổi kết quả | Nhân đôi dữ liệu mà tổng không gấp đôi | Bộ so sánh V3 sai |",
        "|---|---:|---:|---:|---:|",
        *[
            f"| {r['id']} | {r['datasets']} | {r['shuffle_bad']} | {r['double_bad']} | {r['comparator_bad']} |"
            for r in data["v3_raw"]["invariants"]
        ],
        "",
        "## 5. Tự kiểm test của V (cố ý làm hỏng một V, test phải đỏ)",
        "",
    ]
    if data.get("self_check"):
        lines += [
            "| V bị phá | Cách phá | Test chạy | Khi nguyên vẹn | Khi bị phá | Test bắt được? |",
            "|---|---|---|---|---|---|",
        ]
        for r in data["self_check"]:
            caught = "✓" if r["broken"]["failed"] > 0 and r["intact"]["failed"] == 0 else "✗"
            lines.append(
                f"| {r['sabotage']} | {r['what']} | {', '.join(f'`{t}`' for t in r['targets'])} | "
                f"{r['intact']['summary']} | {r['broken']['summary']} | {caught} |"
            )
    else:
        lines.append("— (bỏ qua: chạy với `--quick`).")
    still = (
        [("V1", i) for i in v1["missed"]]
        + [(f"V2 {b['base']}", i) for b in data.get("v2", []) for i in b["missed"]]
        + [("V3", i) for i in v3["missed"]]
    )
    lines += [
        "",
        "## 6. Ca còn lọt và cách giảm rủi ro",
        "",
        "| Node | Ca | Cách giảm rủi ro |",
        "|---|---|---|",
        *[
            f"| {node} | `{i}` | {MITIGATIONS.get(i, 'Reviewer đọc diff + bằng chứng; thêm dữ liệu thử chạm đúng trường hợp.')} |"
            for node, i in still
        ],
    ]
    if not still:
        lines.append("| — | — | Không còn ca lọt trong bộ hiện có (bộ ca vẫn hữu hạn). |")
    lines += [
        "",
        'Lớp bảo vệ chung khi V bỏ sót: Reviewer (J2) xem diff và bảng "Code đo | LLM nói"; sandbox DuckDB tắt truy cập '
        "file ngoài, có timeout và giới hạn bộ nhớ; tối đa 3 vòng sửa rồi chuyển con người.",
        "",
        "## 7. Lỗi tìm thấy khi dựng bộ đo (đã sửa, ca giữ lại trong bộ)",
        "",
        "| Ngày | Node | Lỗi |",
        "|---|---|---|",
        *[f"| {d} | V1 | Ca `{i}` lọt. {n} |" for d, i, n in v1["found_leaks"]],
        *[f"| {d} | {node} | {text} |" for d, node, text in FIXED_DURING_BUILD],
        "",
        "## 8. Cần hỗ trợ",
        "",
        "- Nhờ **người ngoài nhóm** thêm ca khó vào `eval/verifier_bench/v1_redteam.yaml`, `v3_pairs.yaml`, "
        "`v2_mutants/` với `labeled_by: external`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    """Chạy các phần và ghi báo cáo."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="Bỏ V2 (dbt thật) và tự kiểm")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    data: dict = {"date": date.today().isoformat()}
    print("→ V1 red team", flush=True)
    v1_results = v1_bench.run_all()
    data["v1"] = v1_summary(v1_results)
    data["v1_rows"] = [
        {
            "id": r.case.id,
            "label": r.case.label,
            "labeled_by": r.case.labeled_by,
            "blocked": r.blocked,
            "detail": r.detail,
        }
        for r in v1_results
    ]
    print("→ V3 cặp query, dữ liệu ngẫu nhiên, luật viết lại, bất biến", flush=True)
    data["v3_raw"] = v3_bench.run_all(ROOT / "data" / "eval_work" / "verifier_v3")
    data["v3"] = v3_summary(data["v3_raw"])
    if not args.quick:
        print("→ V2 đột biến (dbt build thật)", flush=True)
        data["v2_raw"] = v2_bench.run_all()
        data["v2"] = [v2_summary(base) for base in data["v2_raw"]]
        print("→ Tự kiểm test của V", flush=True)
        data["self_check"] = run_self_check()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "verifier_report.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    (RESULTS / "verifier_report.md").write_text(render(data), encoding="utf-8")
    print(f"Đã ghi {RESULTS / 'verifier_report.md'}")


if __name__ == "__main__":
    main()
