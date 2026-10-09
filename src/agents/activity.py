"""Mô tả việc một node đang làm, để người dùng không phải nhìn màn hình trống khi chờ LLM (planner/codegen 20–60 s).

Mỗi câu ghép từ state THẬT mà node nhận vào (yêu cầu, nguồn, đặc tả, lỗi vòng trước) và mô tả việc của bước đó.
Đây KHÔNG phải nhật ký đo được: web hiển thị kiểu "đang làm", tách khỏi các dòng ✓/✗ do code đo. Không có số giả,
không có % tiến độ giả. Thiếu dữ liệu thì bỏ câu đó, không đoán.
"""

from collections.abc import Callable

from src.agents.nodes.mock_data import DATASET_NAMES
from src.config import get_settings

MAX_ITEMS = 4  # số tên (bảng, cột) tối đa trong một câu
MAX_TEXT = 90  # cắt trích dẫn dài


def _names(items: list[str]) -> str:
    shown = ", ".join(items[:MAX_ITEMS])
    return shown + (f" và {len(items) - MAX_ITEMS} mục khác" if len(items) > MAX_ITEMS else "")


def _quote(text: str) -> str:
    text = " ".join(str(text).split())
    return f"“{text[:MAX_TEXT]}{'…' if len(text) > MAX_TEXT else ''}”"


def _spec(state: dict) -> dict:
    return state.get("spec") or {}


def _sources(state: dict) -> list[str]:
    from_spec = [s.get("name", "") for s in _spec(state).get("sources", []) if s.get("name")]
    return from_spec or [s.get("name", "") for s in state.get("source_catalog", []) if s.get("name")]


def _target(state: dict) -> str:
    return _spec(state).get("target", "")


def _last_error(state: dict) -> str:
    """Lỗi V1/V2 vòng trước (nếu đang trong vòng sửa)."""
    safety, sandbox = state.get("safety") or {}, state.get("sandbox") or {}
    if safety.get("passed") is False and safety.get("issues"):
        return str(safety["issues"][0])
    if sandbox.get("passed") is False and sandbox.get("error"):
        return str(sandbox["error"]).splitlines()[0]
    return ""


def _catalog_names(state: dict) -> list[str]:
    """Tên bảng nguồn Planner sẽ xem: catalog trong state, hoặc (vòng đầu) tên file trong thư mục nguồn."""
    if catalog := state.get("source_catalog"):
        return [s.get("name", "") for s in catalog if s.get("name")]
    folder = get_settings().sources_dir
    return sorted(p.stem for p in folder.glob("*") if p.is_file()) if folder.is_dir() else []


def _planner(state: dict) -> list[str]:
    lines = [f"Đọc yêu cầu {_quote(state.get('request_text', ''))}"]
    if sources := _catalog_names(state):
        lines.append(f"Xem schema và dòng mẫu (đã che PII) của {len(sources)} bảng nguồn: {_names(sources)}")
    if answered := state.get("answered"):
        lines.append(f"Dùng {len(answered)} câu trả lời làm rõ của bạn")
    if feedback := state.get("plan_feedback"):
        lines.append(f"Lập lại kế hoạch theo ghi chú của bạn: {_quote(feedback[-1])}")
    lines += [
        "Chọn bảng đích, mỗi dòng là gì (grain), cột đầu ra và chỉ số",
        "Quyết định ELT hay ETL; điểm nào chưa rõ thì soạn câu hỏi cho bạn",
        "Viết kế hoạch từng bước kèm lý do để bạn duyệt (J1b)",
    ]
    return lines


def _codegen(state: dict) -> list[str]:
    target, spec = _target(state), _spec(state)
    lines = []
    if error := _last_error(state):
        lines.append(f"Sửa lỗi lần {state.get('fix_attempts', 0)}: {_quote(error)}")
    if hint := state.get("rescue_hint"):
        lines.append(f"Áp dụng gợi ý cứu hộ của bạn: {_quote(hint)}")
    if notes := state.get("review_notes"):
        lines.append(f"Sửa theo ghi chú khi duyệt: {_quote(notes[-1])}")
    if sources := _sources(state):
        lines.append(f"Viết model staging cho {len(sources)} nguồn: {_names(sources)}")
    if target:
        columns = [c.get("name", "") for c in spec.get("output_columns", [])]
        lines.append(f"Viết model mart `{target}`" + (f" với {len(columns)} cột: {_names(columns)}" if columns else ""))
    if grain := spec.get("grain"):
        lines.append(f"Mỗi dòng của mart là một giá trị của {_names(grain)}")
    lines.append("Viết DAG Airflow chạy `dbt build`")
    return lines


def _testgen(state: dict) -> list[str]:
    target, spec = _target(state), _spec(state)
    lines = ["Viết một câu SELECT độc lập tính lại kết quả mong đợi từ dữ liệu thô (không xem code pipeline)"]
    if metrics := [m.get("name", "") for m in spec.get("metrics", [])]:
        lines.append(f"Tính lại các chỉ số: {_names(metrics)}")
    if target and (grain := spec.get("grain")):
        lines.append(f"Hệ thống sẽ so hai chiều với `{target}` theo khóa {_names(grain)}")
    if state.get("test_files"):
        lines.append("Sửa câu kiểm tra theo lỗi lần trước")
    return lines


def _optimizer(state: dict) -> list[str]:
    target = _target(state)
    lines = ["Tìm dấu hiệu chậm bằng code: SELECT *, UNION, hàm trong WHERE, truy vấn con tương quan…"]
    if target:
        lines.append(f"Đo thời gian query gốc của `{target}` trên bộ dữ liệu lớn")
    if state.get("opt_attempts"):
        lines.append(f"Đề xuất lần {state['opt_attempts'] + 1}: ứng viên trước chưa qua V3")
    return lines + ["LLM đề xuất bản viết lại; V3 sẽ chạy cả hai và so kết quả bằng code"]


def _quick(text: str) -> Callable[[dict], list[str]]:
    return lambda state: [text]


ACTIVITIES: dict[str, Callable[[dict], list[str]]] = {
    "planner": _planner,
    "codegen": _codegen,
    "testgen": _testgen,
    "optimizer": _optimizer,
    "spec_check": _quick("Soát đặc tả bằng code: tên cột, khóa, nguồn có thật"),
    "ingest": lambda s: [
        f"Nạp {len(_sources(s))} nguồn vào sandbox DuckDB" if _sources(s) else "Nạp nguồn vào sandbox"
    ],
    "profiler": _quick("Soi dữ liệu nguồn bằng code: kiểu cột, % rỗng, khóa trùng, định dạng ngày/tiền"),
    "schema_guard": _quick("So cấu trúc nguồn (cột, kiểu, giá trị phân loại) với bản Reviewer đã duyệt, bằng code"),
    "mock_data": _quick(f"Tạo {len(DATASET_NAMES)} bộ dữ liệu thử (seed cố định): {', '.join(DATASET_NAMES)}"),
    "safety": _quick("Kiểm an toàn bằng code: chặn lệnh ghi, hàm hệ thống, DAG gọi shell"),
    "sandbox_run": _quick("Ghi file đã qua V1 vào workspace, chạy `dbt build` + test trên DuckDB local"),
    "compare": _quick("Chạy SQL gốc và SQL tối ưu trên nhiều bộ dữ liệu, so kết quả từng dòng"),
    "package": _quick("Gom bằng chứng đo được và diff để bạn duyệt"),
}


def activity_for(node: str, state: dict) -> list[str]:
    """Các câu mô tả việc node `node` đang làm, ghép từ state đầu vào; rỗng nếu node không cần mô tả."""
    builder = ACTIVITIES.get(node)
    return [line for line in builder(state or {}) if line] if builder else []
