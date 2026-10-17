"""Sinh dữ liệu mẫu cho chế độ khách của web (frontend/lib/demo/fixtures.ts).

Cách làm: chạy LUỒNG THẬT của API với LLM_PROVIDER=mock trong thư mục tạm (SQLite tạm, dữ liệu nguồn giả lập seed=42;
không đọc .env, không chạm DB dev), chụp chi tiết lần chạy ở từng bước (cả các khung "đang chạy"), rồi làm sạch:
- bỏ đường dẫn máy (workspace), mã lần chạy → dấu giữ chỗ `__RUN__`;
- đổi tên kênh bán thành tên chung (Sàn A, Sàn B, website);
- token/chi phí/thời gian LLM của mock là 0 → điền SỐ LIỆU MẪU (web luôn ghi chú "số liệu mẫu").

Chạy: python scripts/demo_fixtures.py            (chụp + sinh, ~1-2 phút)
      python scripts/demo_fixtures.py --from x.json   (chỉ sinh lại từ bản chụp đã lưu)
      python scripts/demo_fixtures.py --dump x.json   (chụp và giữ bản JSON thô)
"""

import argparse
import asyncio
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "frontend" / "lib" / "demo" / "fixtures.ts"
REQUEST = "Gộp đơn hàng 3 nguồn, tính doanh thu theo ngày"
STOPPED_REQUEST = "Tính doanh thu theo tuần của 3 kênh bán"
RUN_TOKEN = "__RUN__"
RENAMES = [("Shopee", "Sàn A"), ("SHOPEE", "SAN_A"), ("shopee", "san_a"), ("Tiki", "Sàn B"), ("TIKI", "SAN_B")]
RENAMES += [("tiki", "san_b")]
# Số liệu mẫu cho mỗi lượt gọi LLM theo tác vụ: (token vào, token ra, giây). Giá mẫu: $3 / 1M vào, $15 / 1M ra.
SAMPLE_USAGE = {
    "input_gate": (420, 60, 0.9),
    "planner": (3900, 640, 6.2),
    "codegen": (7100, 2480, 14.6),
    "testgen": (4200, 1350, 8.1),
    "optimizer": (3400, 920, 9.3),
}
PRICE_IN, PRICE_OUT = 3 / 1_000_000, 15 / 1_000_000
# Khóa có trong API nhưng web không khai báo trong frontend/lib/types.ts (và không dùng): bỏ để `satisfies` khớp
DROP_KEYS = {"patch"}
DROP_NESTED = {"summary": {"sources"}, "questions": {"normalized"}, "columns": {"uncertain", "flags"}}


# ---------- 1. Chụp luồng thật (mock) ----------


def _isolated_env(tmp: Path) -> None:
    db = f"sqlite+pysqlite:///{(tmp / 'auth.db').as_posix()}"
    os.environ.update(
        {
            "DATABASE_URL": db,
            "MIGRATION_DATABASE_URL": db,
            "SESSION_SECRET": secrets.token_urlsafe(48),
            "APP_ENV": "test",
            "LLM_PROVIDER": "mock",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "LLM_FALLBACK": "none",
            "LANGCHAIN_TRACING_V2": "false",
            "LANGSMITH_TRACING": "false",
            "STORE_PATH": str(tmp / "app.db"),
            "CHECKPOINT_PATH": str(tmp / "checkpoints.db"),
            "SOURCES_DIR": str(tmp / "sources"),
            "WORKSPACES_DIR": str(tmp / "workspaces"),
            "TEMPLATE_DIR": str(REPO / "pipelines" / "template"),
            "DRIFT_GATE_ENABLED": "false",
            "MOCK_LARGE_ROWS": "20000",
        }
    )


async def _capture() -> dict:  # noqa: PLR0915 - kịch bản tuần tự, tách nhỏ chỉ khó đọc hơn
    sys.path.insert(0, str(REPO))
    from alembic import command
    from alembic.config import Config
    from httpx import ASGITransport, AsyncClient

    from src.config import get_settings

    get_settings.cache_clear()
    cfg = Config(str(REPO / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")

    from src.main import app
    from src.services import auth, llm_mock
    from src.services.jobs import get_jobs
    from src.services.seed import SeedConfig, generate_sources

    api = "/api/v1"

    async def login(role: str, name: str) -> AsyncClient:
        password = secrets.token_urlsafe(16)
        auth.create_user(name, name, role, password)
        client = AsyncClient(
            transport=ASGITransport(app=app), base_url="https://test", headers={"X-Requested-With": "demo"}
        )
        response = await client.post(f"{api}/auth/login", json={"username": name, "password": password})
        response.raise_for_status()
        return client

    async def follow(client: AsyncClient, run_id: str) -> list[dict]:
        """Hỏi chi tiết liên tục khi job chạy; giữ mỗi khung khác node/số bước."""
        frames, seen = [], set()
        while True:
            busy = get_jobs().busy(run_id)
            detail = (await client.get(f"{api}/runs/{run_id}")).json()
            key = ((detail.get("current") or {}).get("node"), len(detail.get("events") or []))
            if detail.get("busy") and key not in seen:
                seen.add(key)
                frames.append(detail)
            if not busy:
                break
            await asyncio.sleep(0.03)
        get_jobs().wait(run_id)
        return frames

    async def get(client: AsyncClient, path: str, **params: str) -> dict:
        response = await client.get(f"{api}{path}", params=params)
        response.raise_for_status()
        return response.json()

    generate_sources(SeedConfig(out_dir=get_settings().sources_dir, seed=42, dirty=0.05, rows_per_source=120))
    eng = await login("engineer", "khach")
    rev = await login("reviewer", "khach-duyet")
    data: dict = {}

    run_id = (await eng.post(f"{api}/runs", json={"request_text": REQUEST})).json()["run_id"]
    data["run_id"] = run_id
    data["frames_intake"] = await follow(eng, run_id)
    data["clarify"] = await get(eng, f"/runs/{run_id}")
    answers = {q["id"]: q["options"][0] for q in data["clarify"]["pending"]["questions"]}
    await eng.post(f"{api}/runs/{run_id}/answers", json={"answers": answers})
    data["frames_plan"] = await follow(eng, run_id)
    data["plan"] = await get(eng, f"/runs/{run_id}")
    await eng.post(f"{api}/runs/{run_id}/plan", json={"decision": "approve"})
    data["frames_build"] = await follow(eng, run_id)
    data["review"] = await get(eng, f"/runs/{run_id}")
    data["files"] = await get(eng, f"/runs/{run_id}/files")
    data["catalog"] = await get(eng, f"/runs/{run_id}/catalog")
    data["profiles"] = {
        t["id"]: await get(eng, f"/runs/{run_id}/profile", table=t["id"], dataset="sandbox")
        for t in data["catalog"]["tables"]
    }
    await rev.post(f"{api}/runs/{run_id}/review", json={"decision": "approve", "note": ""})
    data["frames_approve"] = await follow(rev, run_id)
    data["approved"] = await get(rev, f"/runs/{run_id}")

    # Lần chạy dừng: code sinh ra JOIN một bảng không có → sửa tự động hết lượt → cứu hộ → người dùng chọn dừng
    original = llm_mock.HANDLERS["codegen"]

    def broken(variables: dict) -> dict:
        out = original(variables)
        for item in out["files"]:
            if item["path"].startswith("models/marts/"):
                item["content"] = re.sub(
                    r"\{\{\s*ref\('stg_tiki_orders'\)\s*\}\}",
                    "{{ ref('stg_tiki_orders') }} join {{ ref('stg_khuyen_mai_quy') }} using (order_id)",
                    item["content"],
                )
        return out

    llm_mock.HANDLERS["codegen"] = broken
    try:
        bad = (await eng.post(f"{api}/runs", json={"request_text": STOPPED_REQUEST})).json()["run_id"]
        data["stopped_id"] = bad
        await follow(eng, bad)
        pending = (await get(eng, f"/runs/{bad}"))["pending"]
        answers = {q["id"]: q["options"][0] for q in pending["questions"]}
        await eng.post(f"{api}/runs/{bad}/answers", json={"answers": answers})
        await follow(eng, bad)
        await eng.post(f"{api}/runs/{bad}/plan", json={"decision": "approve"})
        await follow(eng, bad)
        await eng.post(f"{api}/runs/{bad}/rescue", json={"action": "abort", "hint": ""})
        await follow(eng, bad)
        data["stopped"] = await get(eng, f"/runs/{bad}")
        data["stopped_files"] = await get(eng, f"/runs/{bad}/files")
    finally:
        llm_mock.HANDLERS["codegen"] = original
    assert data["stopped"]["record"]["status"] == "failed", data["stopped"]["record"]["status"]

    data["status"] = await get(eng, "/status")
    data["sources_catalog"] = await get(eng, "/catalog/sources")
    data["schema_report"] = await get(eng, "/catalog/schema-changes")
    data["errors"] = await get(eng, "/errors")
    data["glossary"] = await get(eng, "/glossary")
    data["sources"] = await get(eng, "/sources")
    for client in (eng, rev):
        await client.aclose()
    return data


def capture() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="p113-demo-"))
    try:
        _isolated_env(tmp)
        return asyncio.run(_capture())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- 2. Làm sạch + điền số liệu mẫu ----------


def _sample_usage(usage: dict) -> dict:
    rows = []
    for row in usage.get("rows", []):
        tin, tout, sec = SAMPLE_USAGE.get(row["task"], (800, 120, 1.5))
        calls = row["calls"]
        rows.append(
            {
                **row,
                "input_tokens": tin * calls,
                "output_tokens": tout * calls,
                "cached_tokens": int(tin * calls * 0.3),
                "cost_usd": round(calls * (tin * PRICE_IN + tout * PRICE_OUT), 4),
                "seconds": round(sec * calls, 1),
                "models": ["mô hình mẫu"],
            }
        )
    return {"rows": rows, "cache_hit_rate": 0.3 if rows else None, "simulated": False}


def _clean_detail(detail: dict) -> dict:
    detail = {k: v for k, v in detail.items() if k not in DROP_KEYS}
    if "usage" in detail:
        detail["usage"] = _sample_usage(detail["usage"])
        rows = detail["usage"]["rows"]
        summary = detail["record"]["summary"]
        summary["tokens"] = sum(r["input_tokens"] + r["output_tokens"] for r in rows)
        summary["cost_usd"] = round(sum(r["cost_usd"] for r in rows), 4)
        summary["llm_calls"] = sum(r["calls"] for r in rows)
        summary["simulated"] = False
        opt = detail.get("optimization") or {}
        if opt.get("decision"):
            opt["llm_cost_usd"] = round(sum(r["cost_usd"] for r in rows if r["task"] == "optimizer"), 4)
    record = detail["record"]
    record["summary"]["workspace"] = None
    record["provider"], record["model"] = "demo", "mô hình mẫu"
    return detail


def _relative_events(detail: dict, starts: list[float]) -> list[float]:
    """finished_at (epoch) → giây kể từ lúc bắt đầu giai đoạn chứa bước đó (web cộng lại theo giờ của phiên khách)."""
    offsets = []
    for event in detail["events"]:
        at = event.get("finished_at") or 0
        start = max((s for s in starts if s <= at), default=starts[0])
        offsets.append(round(at - start, 2))
        event["finished_at"] = 0
    return offsets


def _phase_starts(details: list[dict]) -> list[float]:
    """Mốc bắt đầu mỗi giai đoạn: bước đầu tiên mới xuất hiện trong ảnh chụp kế tiếp (trừ thời lượng của nó)."""
    starts, seen = [], 0
    for detail in details:
        events = detail["events"]
        if len(events) > seen:
            first = events[seen]
            starts.append((first.get("finished_at") or 0) - first["seconds"])
        seen = len(events)
    return starts


def _frames(frames: list[dict], final: dict) -> list[dict]:
    """Khung "đang chạy": chỉ giữ khóa khác ảnh chụp cuối giai đoạn; thời lượng khung = thời gian bước kế tiếp."""
    out = []
    for frame in frames:
        frame = _clean_detail(frame)
        n = len(frame["events"])
        nxt = final["events"][n]["seconds"] if n < len(final["events"]) else 1.0
        patch = {
            k: v for k, v in frame.items() if json.dumps(v, sort_keys=True) != json.dumps(final.get(k), sort_keys=True)
        }
        patch.pop("events", None)  # web cắt danh sách bước theo `events_count`
        cur = patch.get("current")
        if cur:
            cur["started_at"], cur["elapsed_s"] = 0, 0
        out.append({"dur": round(min(max(nxt, 1.2), 4.0), 1), "events_count": n, "patch": patch})
    return out


def _conform(value: object, parent: str = "") -> object:
    """Khớp khuôn web: bỏ khóa trong DROP_NESTED theo khóa cha; trong `spec`, trường null → bỏ (web khai báo tùy chọn)."""
    if isinstance(value, list):
        return [_conform(v, parent) for v in value]
    if not isinstance(value, dict):
        return value
    drop = DROP_NESTED.get(parent, set())
    return {k: _conform(v, k) for k, v in value.items() if k not in drop and not (parent == "spec" and v is None)}


def _scrub(text: str, ids: dict[str, str]) -> str:
    for old, new in RENAMES:
        text = text.replace(old, new)
    for run_id, token in ids.items():
        text = text.replace(run_id, token)
    text = re.sub(r"[A-Za-z]:\\\\[^\"]*p113-demo-[^\"]*", "", text)
    return text


def build(data: dict) -> dict:
    ids = {data["run_id"]: RUN_TOKEN, data["stopped_id"]: RUN_TOKEN}
    data = _conform(json.loads(_scrub(json.dumps(data, ensure_ascii=False), ids)))
    snaps = {k: _clean_detail(data[k]) for k in ("clarify", "plan", "review", "approved")}
    for snap in snaps.values():  # mốc giờ của lần chạy chính do web tính theo dòng thời gian giả lập
        for event in snap["events"]:
            event["finished_at"] = 0
    stopped = _clean_detail(data["stopped"])
    stopped_offsets = _relative_events(stopped, _phase_starts([stopped]) or [0.0])
    phases = {
        "intake": _frames(data["frames_intake"], snaps["clarify"]),
        "plan": _frames(data["frames_plan"], snaps["plan"]),
        "build": _frames(data["frames_build"], snaps["review"]),
        "approve": _frames(data["frames_approve"], snaps["approved"]),
    }
    status = {**data["status"], "llm_provider": "demo", "models": "mô hình mẫu", "simulated": False}
    return {
        "request": _scrub(REQUEST, {}),
        "stoppedRequest": STOPPED_REQUEST,
        "snapshots": snaps,
        "phases": phases,
        "files": data["files"],
        "catalog": data["catalog"],
        "profiles": data["profiles"],
        "stopped": {"detail": stopped, "eventOffsets": stopped_offsets, "files": data["stopped_files"]},
        "status": status,
        "sourcesCatalog": data["sources_catalog"],
        "schemaReport": data["schema_report"],
        "errors": data["errors"],
        "glossary": data["glossary"],
        "sources": data["sources"],
    }


HEADER = """// SINH TỰ ĐỘNG bởi `python scripts/demo_fixtures.py` — không sửa tay.
// Chụp từ luồng thật với LLM_PROVIDER=mock trên dữ liệu nguồn giả lập (không có dữ liệu thật, không có khóa).
// Token/chi phí/thời gian LLM là SỐ LIỆU MẪU; web luôn ghi chú "số liệu mẫu" bên cạnh.
import type { DemoFixtures } from "./types";

export const RUN_TOKEN = "__RUN__";

export const FIXTURES = """


def write_ts(fixtures: dict) -> None:
    body = json.dumps(fixtures, ensure_ascii=False, indent=1)
    leftover = [w for w in ("shopee", "tiki", "p113-demo-", "Users\\\\") if w in body.lower()]
    if leftover:
        raise SystemExit(f"Còn chuỗi cần làm sạch: {leftover}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"{HEADER}{body} satisfies DemoFixtures;\n", encoding="utf-8", newline="\n")
    print(f"Đã ghi {OUT.relative_to(REPO)} ({OUT.stat().st_size // 1024} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="source", type=Path, help="sinh từ bản chụp JSON đã lưu")
    parser.add_argument("--dump", type=Path, help="lưu bản chụp JSON thô (để sinh lại nhanh)")
    args = parser.parse_args()
    data = json.loads(args.source.read_text(encoding="utf-8")) if args.source else capture()
    if args.dump:
        args.dump.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    write_ts(build(data))


if __name__ == "__main__":
    main()
