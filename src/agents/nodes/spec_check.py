"""V0 Soát Spec (code thuần): chặn khi còn điểm chưa biết, thiếu trường bắt buộc, hoặc mode không khớp tín hiệu."""

import re

from src.agents.state import PipelineState
from src.models.spec import PipelineSpec, decide_mode, signals_from_sources

IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _required_fields(spec: PipelineSpec) -> list[str]:
    errors = []
    if not IDENTIFIER_RE.match(spec.target):
        errors.append("Thiếu hoặc sai tên bảng đích (target phải là snake_case).")
    if not spec.sources:
        errors.append("Chưa chọn nguồn dữ liệu nào.")
    if not spec.grain:
        errors.append("Chưa xác định grain (cột xác định một dòng).")
    names = [c.name for c in spec.output_columns]
    if len(names) != len(set(names)) or not names:
        errors.append("Danh sách cột đầu ra rỗng hoặc bị trùng tên.")
    errors.extend(
        f"Cột grain '{g}' không nằm trong cột đầu ra; grain chỉ được chọn trong: {', '.join(names)}."
        for g in spec.grain
        if g not in names
    )
    return errors


def _sources_exist(spec: PipelineSpec, catalog: list[dict]) -> list[str]:
    known = {item["name"]: item["kind"] for item in catalog}
    return [
        f"Nguồn '{s.name}' không có trong danh mục bạn được phép dùng (không tồn tại hoặc bạn chưa được cấp quyền xem)."
        if s.name not in known
        else f"Nguồn '{s.name}' sai loại ({s.kind} ≠ {known[s.name]})."
        for s in spec.sources
        if known.get(s.name) != s.kind
    ]


def _references_exist(spec: PipelineSpec) -> list[str]:
    """Khóa ngoại `bang.cot` thành test `relationships` tới `ref('bang')`: bảng phải là model có thật (đích hoặc `stg_<nguồn>`)."""
    models = {spec.target} | {f"stg_{s.name}" for s in spec.sources}
    errors = []
    for column in spec.output_columns:
        if not column.references:
            continue
        table, _, field = column.references.partition(".")
        if table not in models or not field:
            errors.append(
                f"Cột '{column.name}': references '{column.references}' không trỏ tới model có thật "
                f"(chỉ được: {', '.join(sorted(models))}). Để trống nếu không phải khóa ngoại (đừng ghi nguồn gốc cột)."
            )
        elif table == spec.target and field not in {c.name for c in spec.output_columns}:
            errors.append(
                f"Cột '{column.name}': references '{column.references}' trỏ tới cột không có trong bảng đích."
            )
    return errors


def _unknowns(spec: PipelineSpec) -> list[str]:
    if not spec.unknowns:
        return []
    errors = [f"Còn {len(spec.unknowns)} điểm chưa rõ: " + "; ".join(spec.unknowns)]
    if not spec.questions:
        errors.append("Có điểm chưa rõ nhưng Planner không đặt câu hỏi làm rõ.")
    return errors


NUMERIC_PREFIXES = ("BIGINT", "INT", "HUGEINT", "SMALLINT", "DOUBLE", "FLOAT", "REAL", "DECIMAL", "NUMERIC")


def _dimensions_in_grain(spec: PipelineSpec) -> list[str]:
    """Bảng gộp theo phân loại (có chỉ số, grain không có cột mã): cột không phải số phải nằm trong grain.

    Grain có cột mã (`id`, `*_id`) thì cột mô tả (tên, chức danh) phụ thuộc vào mã, không gây trùng dòng → bỏ qua.
    """
    if not spec.metrics or any(g.lower() == "id" or g.lower().endswith("_id") for g in spec.grain):
        return []
    return [
        f"Cột '{c.name}' ({c.type}) không phải chỉ số nhưng không nằm trong grain {spec.grain}: thêm vào grain hoặc bỏ."
        for c in spec.output_columns
        if c.name not in spec.grain and not c.type.upper().startswith(NUMERIC_PREFIXES)
    ]


def _mode_matches(spec: PipelineSpec) -> list[str]:
    expected, _ = decide_mode(signals_from_sources(spec.sources, spec.signals))
    return [] if spec.mode == expected else [f"Mode {spec.mode} không khớp tín hiệu (phải là {expected})."]


def _options_valid(spec: PipelineSpec, catalog: list[dict]) -> list[str]:
    """Lựa chọn pipeline phải nhất quán: nạp phần mới cần cột thời gian có thật ở một nguồn được chọn."""
    options = spec.options
    errors = []
    if options.load_mode == "incremental":
        columns = {
            c for item in catalog if item["name"] in {s.name for s in spec.sources} for c in item.get("columns", {})
        }
        if not options.incremental_column:
            errors.append("Nạp phần mới cần cột thời gian (incremental_column) nhưng chưa chọn cột nào.")
        elif options.incremental_column not in columns:
            errors.append(f"Cột thời gian '{options.incremental_column}' không có ở nguồn nào được chọn.")
    known = {s.name for s in spec.sources}
    errors += [
        f"Kết nối của nguồn '{c.source}' không khớp nguồn trong đặc tả."
        for c in options.connections
        if c.source not in known
    ]
    return errors


def check_spec(spec_data: dict, catalog: list[dict]) -> list[str]:
    """Danh sách lỗi của đặc tả (rỗng = đạt)."""
    if not spec_data:
        return ["Chưa có đặc tả hợp lệ từ Planner."]
    spec = PipelineSpec.model_validate(spec_data)
    checks = _unknowns(spec) + _required_fields(spec) + _references_exist(spec) + _dimensions_in_grain(spec)
    return checks + _sources_exist(spec, catalog) + _mode_matches(spec) + _options_valid(spec, catalog)


def spec_check_node(state: PipelineState) -> dict:
    """Soát spec; giữ lỗi định dạng của Planner nếu có."""
    if not state.get("spec") and state.get("spec_errors"):
        return {"spec_errors": state["spec_errors"]}
    return {"spec_errors": check_spec(state.get("spec", {}), state.get("source_catalog", []))}
