"""E3 Codegen (LLM): spec + hồ sơ + danh mục thật → model dbt + DAG Airflow."""

import logging
import re

from src.agents.nodes.common import memory_notes, usage_of
from src.agents.state import PipelineState
from src.agents.tools.dbt_tools import is_allowed_path
from src.agents.tools.scrub import prompt_error
from src.services.error_memory import classify_error, error_signature, get_error_memory
from src.services.llm import LLMOutputError, call_llm, parse_json_output, to_json
from src.services.llm_context import context_for_state
from src.services.prompt_context import spec_for_build

logger = logging.getLogger(__name__)


def last_error(state: PipelineState) -> str:
    """Lỗi gần nhất của V1/V2 (rỗng nếu chưa có)."""
    safety, sandbox = state.get("safety", {}), state.get("sandbox", {})
    if safety and not safety.get("passed", True):
        return "\n".join(safety.get("issues", []))
    if sandbox and not sandbox.get("passed", True):
        return sandbox.get("error", "")
    return ""


def code_error(state: PipelineState) -> str:
    """Lỗi thuộc phần Coder viết; lỗi của file test (tests/...) là việc của Testgen."""
    return "\n".join(line for line in last_error(state).splitlines() if not line.startswith("tests/"))


REF_RE = re.compile(r"ref\(\s*['\"](\w+)['\"]\s*\)")


def needs_fix(state: PipelineState) -> bool:
    """Vòng sửa: đã có code và có lỗi, ghi chú Reviewer hoặc gợi ý cứu hộ."""
    return bool(
        state.get("code_files") and (last_error(state) or state.get("review_notes") or state.get("rescue_hint"))
    )


def _model(path: str) -> str:
    return path.rsplit("/", 1)[-1].removesuffix(".sql")


def related_files(files: dict[str, str], error: str) -> dict[str, str]:
    """File bị lỗi nêu tên + model chúng ref() tới + model ref() tới chúng (quy tắc 2.2-14: không gửi cả bộ code).

    Lỗi không nêu file nào (ví dụ ghi chú Reviewer, lỗi dbt chung) → gửi đủ mọi file.
    """
    named = {path for path in files if path in error}
    if not named:
        return files
    refs = {path: set(REF_RE.findall(content)) for path, content in files.items()}
    named_models = {_model(path) for path in named}
    upstream = {name for path in named for name in refs[path]}
    keep = named | {p for p in files if _model(p) in upstream or refs[p] & named_models}
    return {path: files[path] for path in sorted(keep)}


def previous_code(state: PipelineState) -> str:
    """Code vòng trước, chỉ gửi khi cần sửa; có lỗi nêu tên file thì chỉ gửi file liên quan."""
    if not needs_fix(state):
        return "(chưa có)"
    return to_json(related_files(state["code_files"], code_error(state)))


def error_hints(error: str) -> list[dict]:
    """Tối đa 3 mục sổ lỗi ĐÃ DUYỆT giống lỗi hiện tại (chỉ là gợi ý)."""
    if not error:
        return []
    entries = get_error_memory().approved_hints(error_signature(error), classify_error(error))
    return [{"code": e.code, "description": prompt_error(e.description, 300), "fix": e.fix} for e in entries]


def _profile_context(state: PipelineState) -> dict:
    """Hồ sơ dữ liệu cho prompt, cắt theo mức truy cập của từng nguồn (cửa duy nhất: llm_context)."""
    profile = state.get("profile", {})
    return context_for_state(state, tables=list(profile)).build_profile(profile)


def codegen_variables(state: PipelineState) -> dict[str, str]:
    """Biến điền vào prompt codegen."""
    error = code_error(state)
    return {
        "spec": to_json(spec_for_build(state.get("spec", {}))),
        "profile": to_json(_profile_context(state)),
        "last_error": prompt_error(error) or "(không có)",
        "previous_code": previous_code(state),
        "error_hints": to_json(error_hints(error)),
        "memory_notes": to_json(memory_notes(state)),
        "review_notes": to_json(state.get("review_notes", [])),
        "rescue_hint": state.get("rescue_hint") or "(không có)",
    }


def only_test_errors(state: PipelineState) -> bool:
    """Lỗi chỉ nằm ở file test và không có gợi ý cứu hộ → giữ nguyên code, không gọi LLM."""
    return bool(
        last_error(state) and not code_error(state) and state.get("code_files") and not state.get("rescue_hint")
    )


def normalize_file(path: str, content: str) -> str:
    """Bỏ dấu `;` cuối file SQL: dbt nhúng model ephemeral vào model khác nên `;` làm hỏng câu ở model gọi nó."""
    return content.rstrip().rstrip(";").rstrip() + "\n" if path.endswith(".sql") else content


SYSTEM_FILES = {"dbt_project.yml", "profiles.yml", "packages.yml", "sources.yml", "selectors.yml"}


def is_system_file(path: str) -> bool:
    """File cấu hình do hệ thống quản lý (dbt_project, khai báo source) hoặc yml trong models/ (của Testgen)."""
    normalized = path.replace("\\", "/")
    is_model_yml = normalized.startswith("models/") and normalized.endswith((".yml", ".yaml"))
    return normalized.rsplit("/", 1)[-1] in SYSTEM_FILES or is_model_yml


NOTE_SUFFIXES = (".txt", ".md")


def is_misplaced_field(path: str) -> bool:
    """Ghi chú đặt nhầm vào danh sách files: mục ở thư mục gốc không đuôi (`notes`, smoke 2026-10-05) hoặc file ghi chú
    `.txt`/`.md` (`notes.txt`, golden g09 2026-10-05).

    Đường dẫn lạ như `../x.sql` KHÔNG thuộc loại này: giữ lại để V1 chặn và ghi bằng chứng.
    """
    if "/" in path or "\\" in path or ".." in path or ":" in path:
        return False
    return "." not in path or path.lower().endswith(NOTE_SUFFIXES)


def drop_system_files(files: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Bỏ file hệ thống mà Coder tự viết (LLM thật hay viết lại dbt_project.yml/sources.yml → trùng source)
    và mục không phải file (LLM nhầm trường `notes` thành file)."""
    dropped = sorted(p for p in files if is_system_file(p))
    misplaced = sorted(p for p in files if is_misplaced_field(p))
    kept = {p: c for p, c in files.items() if p not in dropped and p not in misplaced}
    note = [f"Hệ thống bỏ {', '.join(dropped)}: file cấu hình do hệ thống quản lý."] if dropped else []
    note += [f"Hệ thống bỏ mục không phải file: {', '.join(misplaced)}."] if misplaced else []
    return kept, note


def files_of(data: dict) -> dict[str, str]:
    """`files` của LLM: danh sách {path, content} (structured output) hoặc object đường dẫn → nội dung (cũ)."""
    raw = data.get("files") or {}
    if isinstance(raw, dict):
        pairs = raw.items()
    else:
        pairs = ((f.get("path", ""), f.get("content", "")) for f in raw if isinstance(f, dict))
    return {str(k): normalize_file(str(k), str(v)) for k, v in pairs if k}


def carry_over(previous: dict[str, str], returned: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """File cũ giữ lại ở vòng sửa, trừ file có đường dẫn V1 đã chặn mà LLM không trả lại.

    LLM chỉ trả file đã đổi nên không có cách xóa file; nếu giữ, V1 chặn mãi tới bước cứu hộ (golden g09 2026-10-05).
    File bị bỏ chưa từng được ghi ra đĩa; lần chặn đầu đã nằm trong bằng chứng V1 của vòng trước.
    """
    blocked = sorted(p for p in previous if not is_allowed_path(p) and p not in returned)
    return {p: c for p, c in previous.items() if p not in blocked}, blocked


def _generate(state: PipelineState) -> dict:
    response = call_llm("codegen", codegen_variables(state))
    try:
        data = parse_json_output(response.text)
        files = files_of(data)
        blocked_note: list[str] = []
        if needs_fix(state):  # vòng sửa: LLM chỉ trả file đã đổi, file khác giữ nguyên
            kept, blocked = carry_over(state["code_files"], files)
            files = {**kept, **files}
            blocked_note = [f"Hệ thống bỏ file bị V1 chặn ở vòng trước: {', '.join(blocked)}."] if blocked else []
        files, dropped_note = drop_system_files(files)
        notes = [str(n) for n in data.get("notes") or []] + dropped_note + blocked_note
    except LLMOutputError as exc:
        logger.warning("codegen output invalid", extra={"error": str(exc)})
        files, notes = {}, [f"Codegen trả về sai định dạng: {exc}"]
    return {"code_files": files, "code_notes": notes, "llm_usage": usage_of(response)}


def codegen_node(state: PipelineState) -> dict:
    """Sinh code (hoặc giữ nguyên khi chỉ test lỗi); reset kết quả tối ưu cũ vì code có thể đã đổi."""
    generated = {"code_files": state["code_files"]} if only_test_errors(state) else _generate(state)
    return {
        **generated,
        "optimization": {},
        "opt_candidate": {},
        "opt_attempts": 0,
        "rescue_hint": "",
    }
