"""Ngữ cảnh gọn gửi LLM, schema đầu ra strict, cấu hình theo node, ghi nhận cache (U1)."""

from pathlib import Path

import duckdb
import pytest

from src.agents.nodes.planner import fill_sources
from src.agents.tools.duckdb_tools import explain_outline
from src.config import Settings
from src.models.llm_outputs import OUTPUT_MODELS, output_schema
from src.services.cost import cache_hit_rate
from src.services.llm import LLMRequest, UsageInfo, _response, openai_response_format
from src.services.prompt_context import compact_catalog, compact_profile, referenced_schema, spec_for_build

SPEC = {
    "request_text": "doanh thu ngày",
    "mode": "ELT",
    "mode_reason": "Mặc định ELT",
    "sources": [{"name": "shopee_orders", "kind": "csv", "path": "F:/may/toi/shopee_orders.csv"}],
    "target": "fct_daily_revenue",
    "grain": ["order_date"],
    "output_columns": [{"name": "order_date", "type": "DATE", "description": "", "references": ""}],
    "metrics": [],
    "unknowns": [],
    "questions": [],
    "decisions": {"q_status": "Chỉ đơn hoàn tất"},
    "signals": {"restricted_pii": False},
    "plan_summary": "Tóm tắt cho người duyệt",
    "plan": [{"title": "Làm sạch", "detail": "đọc ngày", "reason": "ngày lẫn định dạng"}],
}


def test_spec_for_build_keeps_only_what_codegen_and_testgen_use():
    out = spec_for_build(SPEC)
    assert out["sources"] == ["shopee_orders"]  # không lộ đường dẫn máy
    assert out["output_columns"] == [{"name": "order_date", "type": "DATE"}]
    assert out["decisions"] == {"q_status": "Chỉ đơn hoàn tất"}
    assert out["plan"] == [{"title": "Làm sạch", "detail": "đọc ngày"}]
    for dropped in ("mode_reason", "signals", "unknowns", "questions", "plan_summary", "metrics"):
        assert dropped not in out


def test_compact_profile_drops_redundant_fields():
    profile = {
        "orders": {
            "rows": 3,
            "columns": {
                "amount": {
                    "type": "VARCHAR",
                    "nulls": 1,
                    "null_pct": 33.3,
                    "examples": ["1.000"],
                    "date_formats": [],
                    "duckdb_parse": "try_cast(x)",
                    "parse_failures": 0,
                }
            },
            "key_column": "",
            "duplicate_keys": 0,
            "money_columns": ["amount"],
        }
    }
    out = compact_profile(profile)["orders"]
    assert out == {
        "rows": 3,
        "columns": {
            "amount": {"type": "VARCHAR", "null_pct": 33.3, "duckdb_parse": "try_cast(x)"}  # không gửi giá trị mẫu
        },
    }


def test_compact_profile_keeps_parse_failures_and_keys():
    profile = {"t": {"rows": 2, "columns": {"d": {"parse_failures": 2}}, "key_column": "id", "duplicate_keys": 1}}
    out = compact_profile(profile)["t"]
    assert out["columns"]["d"]["parse_failures"] == 2
    assert (out["key_column"], out["duplicate_keys"]) == ("id", 1)


def test_compact_catalog_sends_stats_not_sample_or_path():
    """CLAUDE.md 2.3: Planner chỉ thấy cấu trúc + con số do code đếm; dòng mẫu và đường dẫn không gửi."""
    stats = {"rows": 2, "key_column": "id", "repeated_keys": 0}
    catalog = [
        {
            "name": "orders",
            "kind": "csv",
            "path": "C:/secret/orders.csv",
            "table": "",
            "columns": {"id": "VARCHAR", "amount": "BIGINT"},
            "sample": [{"id": "A", "amount": 5}, {"amount": 7, "id": "B"}],
            "stats": stats,
        }
    ]
    out = compact_catalog(catalog)
    assert out == [{"name": "orders", "kind": "csv", "columns": {"id": "VARCHAR", "amount": "BIGINT"}, "stats": stats}]


def test_fill_sources_takes_kind_and_path_from_catalog():
    catalog = [{"name": "orders", "kind": "csv", "path": "data/orders.csv"}]
    data = fill_sources({"sources": ["orders", {"name": "bia"}]}, catalog)
    assert data["sources"] == [
        {"name": "orders", "kind": "csv", "path": "data/orders.csv"},
        {"name": "bia", "kind": "", "path": ""},  # tên lạ: kind rỗng → V0 chặn "không có trong thư mục"
    ]


def test_referenced_schema_keeps_only_tables_in_query():
    catalog = {"main": {"stg_a": {"x": "INT"}, "stg_b": {"y": "INT"}}, "raw": {"a": {"x": "VARCHAR"}}}
    assert referenced_schema("select x from main.stg_a", catalog) == {"main": {"stg_a": {"x": "INT"}}}
    assert referenced_schema("không phải sql (((", catalog) == catalog


def test_explain_outline_is_compact_operator_tree(tmp_path: Path):
    db = tmp_path / "x.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("create table t as select range as i, range % 3 as g from range(100)")
    text = explain_outline(db, "select g, count(*) from t where i > 5 group by g")
    assert text.startswith("total ")
    assert "SEQ_SCAN" in text and "rows=" in text
    assert "─" not in text and "EXPLAIN" not in text  # không có bảng kẻ khung, không lặp lại câu truy vấn


def _walk(node, path="$"):
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, f"{path}[{i}]")


@pytest.mark.parametrize("task", sorted(OUTPUT_MODELS))
def test_output_schema_meets_openai_strict_rules(task: str):
    schema = output_schema(task)
    for path, node in _walk(schema):
        assert not (isinstance(node, dict) and "$ref" in node), f"{path}: còn $ref"
        if isinstance(node, dict) and node.get("type") == "object":
            assert node.get("additionalProperties") is False, f"{path}: thiếu additionalProperties=false"
            assert set(node.get("required", [])) == set(node.get("properties", {})), f"{path}: có trường không bắt buộc"


def test_openai_response_format_follows_switch():
    on = openai_response_format(Settings(llm_structured_output=True), "codegen")
    assert on["type"] == "json_schema" and on["json_schema"]["strict"] is True
    assert openai_response_format(Settings(llm_structured_output=False), "codegen") == {"type": "json_object"}
    assert openai_response_format(Settings(), "khong-co") == {"type": "json_object"}


def test_temperature_and_max_tokens_per_task():
    settings = Settings(llm_temperature=0.7, llm_max_tokens=5000)
    assert settings.temperature_for("planner") == 0.0
    assert settings.temperature_for("codegen") == 0.2  # Codegen thấp, không quá 0.2
    assert settings.max_tokens_for("codegen") == 5000  # không vượt trần chung
    assert settings.max_tokens_for("testgen") == 5000
    assert settings.max_tokens_for("optimizer") == 5000  # trần riêng 16.000 (từ thời dùng Opus) bị trần chung chặn
    assert Settings().max_tokens_for("optimizer") == 16000


class _Message:
    text = "{}"
    usage_metadata = {"input_tokens": 2000, "output_tokens": 10, "input_token_details": {"cache_read": 1536}}


def test_response_records_cached_tokens():
    info = UsageInfo(provider="openai", model="gpt-5.6-luna", input_tokens=0, output_tokens=0, started=0.0)
    usage = _response(LLMRequest(task="planner", variables={}), _Message(), info).usage
    assert (usage.input_tokens, usage.cached_tokens) == (2000, 1536)


def test_cache_hit_rate_ignores_simulated_calls():
    assert cache_hit_rate([{"input_tokens": 100, "cached_tokens": 0, "simulated": True}]) is None
    real = [{"input_tokens": 1000, "cached_tokens": 500}, {"input_tokens": 1000, "cached_tokens": 0}]
    assert cache_hit_rate(real) == 0.25
