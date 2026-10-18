"""Dữ liệu mẫu của chế độ khách (frontend/lib/demo/fixtures.ts, sinh bởi scripts/demo_fixtures.py).

Kiểm bằng code (V, 0 token): bản đã commit không chứa đường dẫn máy, tên kênh bán thật, chuỗi giống khóa/kết nối;
các bước làm sạch của script làm đúng việc.
"""

import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "frontend" / "lib" / "demo" / "fixtures.ts"


def _script():
    spec = importlib.util.spec_from_file_location("demo_fixtures", REPO / "scripts" / "demo_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_fixtures_are_clean():
    text = FIXTURES.read_text(encoding="utf-8")
    lowered = text.lower()
    for word in ("shopee", "tiki", "p113-demo-", "\\\\users\\\\", "/home/", "/tmp/"):
        assert word not in lowered, word
    assert not re.search(r"(?i)(postgres(ql)?|mysql|duckdb)://", text)  # chuỗi kết nối
    assert not re.search(r"(?i)(sk-[a-z0-9]{16,}|api[_-]?key\"\s*:\s*\"[^\"]+)", text)  # khóa API
    assert '"workspace": null' in text and '"simulated": false' in text
    assert "satisfies DemoFixtures" in text


def test_committed_fixtures_cover_required_states():
    text = FIXTURES.read_text(encoding="utf-8")
    body = text[text.index("export const FIXTURES = ") + len("export const FIXTURES = ") : text.rindex(" satisfies")]
    data = json.loads(body)
    snaps = data["snapshots"]
    assert snaps["approved"]["record"]["status"] == "approved"
    assert snaps["approved"]["optimization"]["decision"] == "applied"  # bản hoàn tất có tối ưu được áp dụng
    assert all(e["equal"] for e in snaps["approved"]["optimization"]["equivalence"])
    assert snaps["review"]["record"]["status"] == "waiting_review"
    assert data["stopped"]["detail"]["record"]["status"] == "failed"
    assert all(data["phases"][p] for p in ("intake", "plan", "build", "approve"))  # khung "đang chạy"
    assert "models/marts/fct_daily_revenue.sql" in data["files"]["code_files"]
    assert any(p.startswith("dags/") for p in data["files"]["code_files"])


def test_scrub_renames_sources_and_run_ids():
    script = _script()
    text = script._scrub(
        '{"a": "shopee_orders Shopee tiki_orders", "id": "abc123", "w": "C:\\\\x\\\\p113-demo-1\\\\y"}',
        {"abc123": "__RUN__"},
    )
    assert "shopee" not in text.lower() and "tiki" not in text.lower()
    assert "san_a_orders" in text and "Sàn A" in text and "__RUN__" in text
    assert "p113-demo-" not in text


def test_conform_drops_unknown_keys_and_null_spec_fields():
    script = _script()
    data = {
        "record": {"summary": {"sources": ["x"], "target": "t"}},
        "pending": {"questions": [{"id": "q", "normalized": "n"}]},
        "spec": {"target": "t", "grain": None},
    }
    out = script._conform(data)
    assert out["record"]["summary"] == {"target": "t"}
    assert out["pending"]["questions"] == [{"id": "q"}]
    assert out["spec"] == {"target": "t"}


def test_sample_usage_is_marked_and_priced():
    script = _script()
    usage = script._sample_usage({"rows": [{"task": "codegen", "calls": 2}], "simulated": True})
    row = usage["rows"][0]
    assert usage["simulated"] is False and row["models"] == ["mô hình mẫu"]
    assert row["input_tokens"] == 2 * script.SAMPLE_USAGE["codegen"][0] and row["cost_usd"] > 0
