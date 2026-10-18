// Bộ lọc danh sách lần chạy theo đường dẫn (/runs?loc=…): thẻ thống kê trang chủ bấm vào là lọc (CLAUDE.md 9.4).
// Số trên thẻ và danh sách sau khi lọc dùng CHUNG hàm ở đây nên luôn khớp nhau.

import type { CurrentUser, RunRecord } from "./types";

import { waitingFor } from "@/components/NotificationBell";

export const RUN_FILTERS = {
  "cua-toi": {
    label: "Yêu cầu của tôi",
    test: (run: RunRecord, user: CurrentUser | null) => run.requester === user?.name,
  },
  "cho-toi": {
    label: "Chờ tôi xử lý",
    test: (run: RunRecord, user: CurrentUser | null) => waitingFor(user, [run]).length > 0,
  },
  "cho-reviewer": {
    label: "Yêu cầu của tôi đang chờ Reviewer",
    test: (run: RunRecord, user: CurrentUser | null) => run.requester === user?.name && run.status === "waiting_review",
  },
  "dang-chay": {
    label: "Đang chạy (Giám sát)",
    test: (run: RunRecord) => run.status === "running",
  },
  "tam-dung": {
    label: "Đã tạm dừng",
    test: (run: RunRecord) => run.status === "paused",
  },
  "da-duyet": {
    label: "Yêu cầu của tôi đã duyệt",
    test: (run: RunRecord, user: CurrentUser | null) => run.requester === user?.name && run.status === "approved",
  },
} as const;

export type RunFilterKey = keyof typeof RUN_FILTERS;

export function isRunFilter(key: string | null): key is RunFilterKey {
  return key !== null && key in RUN_FILTERS;
}

export function filterRuns(runs: RunRecord[], key: RunFilterKey, user: CurrentUser | null): RunRecord[] {
  return runs.filter((run) => RUN_FILTERS[key].test(run, user));
}

export function runFilterHref(key: RunFilterKey): string {
  return `/runs?loc=${key}`;
}
