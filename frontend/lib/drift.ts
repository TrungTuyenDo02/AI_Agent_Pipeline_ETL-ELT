import type { DriftSeverity, PatchAction } from "./types";

// Nhãn tiếng Việt cho các loại thay đổi cấu trúc nguồn và mức độ (dùng ở chuông, trang Thay đổi cấu trúc).

export const CHANGE_LABELS: Record<string, string> = {
  column_added: "Thêm cột",
  column_removed: "Xóa cột",
  possible_rename: "Nghi đổi tên cột",
  type_widened: "Mở rộng kiểu dữ liệu",
  type_narrowed: "Thu hẹp kiểu dữ liệu",
  type_incompatible: "Đổi kiểu không tương thích",
  nullable_changed: "Cho phép rỗng",
  nullable_tightened: "Thành NOT NULL",
  table_removed: "Xóa bảng",
  stat_null_increase: "Cột rỗng nhiều hơn",
  stat_rowcount: "Số dòng lệch nhiều",
  stat_new_shape: "Có dạng giá trị mới",
  stat_range_shift: "Khoảng giá trị lệch",
};

export const SEVERITY_LABELS: Record<DriftSeverity, { label: string; tone: string }> = {
  breaking: { label: "Chặn", tone: "danger" },
  warning: { label: "Cảnh báo", tone: "warn" },
  info: { label: "Thông tin", tone: "info" },
};

export const ROLE_LABELS: Record<string, string> = {
  staging: "Làm sạch",
  mart: "Bảng đích",
  sources: "Khai báo nguồn",
  test: "Test",
  dag: "DAG",
};

export const PATCH_ACTIONS: Record<PatchAction, { label: string; tone: string }> = {
  none: { label: "Không cần sửa", tone: "muted" },
  code: { label: "Tự sửa bằng code", tone: "ok" },
  llm: { label: "Cần AI", tone: "warn" },
  ask: { label: "Cần bạn chọn", tone: "info" },
  blocked: { label: "Không vá được", tone: "danger" },
};
