// Tiến độ dự án hiện ở trang /docs. NHÓM TỰ SỬA FILE NÀY — trang tự tính thanh "x/y mục đã xong".
// Trạng thái: "done" (đã xong) · "doing" (đang làm) · "todo" (chưa làm) · "unknown" (chưa cập nhật, mặc định).
// Không đoán: mục nào chưa kiểm thì để "unknown". `note` là ghi chú ngắn (có thể để trống).

export type ItemStatus = "done" | "doing" | "todo" | "unknown";

export interface ProjectItem {
  title: string;
  group: "Cơ bản" | "Nâng cao" | "Thêm";
  status: ItemStatus;
  note: string;
}

export const PROJECT_STATUS: ProjectItem[] = [
  // Cơ bản
  { group: "Cơ bản", title: "Web triển khai online", status: "unknown", note: "" },
  { group: "Cơ bản", title: "Hai vai Engineer và Reviewer", status: "unknown", note: "" },
  { group: "Cơ bản", title: "Nhập yêu cầu bằng lời → sinh model dbt và DAG Airflow", status: "unknown", note: "" },
  { group: "Cơ bản", title: "Chạy thử trong sandbox", status: "unknown", note: "" },
  { group: "Cơ bản", title: "Người duyệt xem diff trước khi lên hệ thống thật", status: "unknown", note: "" },
  // Nâng cao
  { group: "Nâng cao", title: "Agent tối ưu truy vấn chậm", status: "unknown", note: "" },
  { group: "Nâng cao", title: "Đo độ đúng và so sánh thời gian, chi phí với bản gốc", status: "unknown", note: "" },
  { group: "Nâng cao", title: "Tự sinh test cho pipeline", status: "unknown", note: "" },
  // Thêm
  { group: "Thêm", title: "Chế độ khách có hướng dẫn", status: "doing", note: "" },
  { group: "Thêm", title: "Trang tài liệu này", status: "doing", note: "" },
];

/** Thành viên nhóm hiện ở mục "Nhóm thực hiện" của /docs. */
export const PROJECT_TEAM: string[] = ["[ĐIỀN TÊN THÀNH VIÊN]"];

export const STATUS_TEXT: Record<ItemStatus, string> = {
  done: "Đã xong",
  doing: "Đang làm",
  todo: "Chưa làm",
  unknown: "Chưa cập nhật",
};

/** Số mục đã xong / tổng số mục (thanh tổng quan). */
export function progressOf(items: ProjectItem[]): { done: number; total: number; pct: number } {
  const done = items.filter((item) => item.status === "done").length;
  return { done, total: items.length, pct: items.length ? Math.round((done / items.length) * 100) : 0 };
}
