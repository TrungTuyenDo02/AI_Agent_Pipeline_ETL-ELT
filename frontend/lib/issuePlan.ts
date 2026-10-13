// Kế hoạch xử lý / bỏ qua cảnh báo dữ liệu nguồn (CLAUDE.md yêu cầu 5).
// Backend CHƯA có API lưu quyết định này → lưu trong trình duyệt (localStorage), chỉ người dùng này thấy.
// TODO(thay bằng API): khi backend có endpoint, chỉ sửa `load`/`save` dưới đây; giao diện giữ nguyên.

import { useCallback, useEffect, useState } from "react";

export interface IssueDecision {
  /** bảng + cột + nội dung cảnh báo: định danh ổn định giữa các lần đo */
  key: string;
  table: string;
  column: string;
  text: string;
  kind: "plan" | "skip";
  reason?: string;
  at: string;
}

const STORAGE_KEY = "p113.issue-decisions";
const EVENT = "p113-issue-decisions";

export const issueKey = (table: string, column: string, text: string) => `${table}|${column}|${text}`;

function load(): IssueDecision[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as IssueDecision[]) : [];
  } catch {
    return [];
  }
}

function save(items: IssueDecision[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // trình duyệt chặn lưu trữ: quyết định chỉ còn trong phiên này
  }
  window.dispatchEvent(new Event(EVENT));
}

/** Danh sách quyết định + hàm ghi/bỏ; đồng bộ giữa các thẻ trên cùng trang. */
export function useIssueDecisions() {
  const [items, setItems] = useState<IssueDecision[]>([]);
  useEffect(() => {
    const sync = () => setItems(load());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  const decide = useCallback((decision: Omit<IssueDecision, "at">) => {
    save([...load().filter((d) => d.key !== decision.key), { ...decision, at: new Date().toISOString() }]);
  }, []);
  const undo = useCallback((key: string) => save(load().filter((d) => d.key !== key)), []);
  return { items, decide, undo };
}

/** Câu yêu cầu điền sẵn ở trang chủ từ các mục trong kế hoạch xử lý của một bảng. */
export function draftRequest(table: string, plan: IssueDecision[]): string {
  const lines = plan.map((d) => `- ${d.column ? `cột ${d.column}: ` : ""}${d.text}`);
  return `Làm sạch bảng ${table} trước khi dùng, xử lý các điểm sau:\n${lines.join("\n")}`;
}
