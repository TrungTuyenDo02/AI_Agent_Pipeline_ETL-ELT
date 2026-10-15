"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CHANGE_LABELS } from "@/lib/drift";
import { STATUS_LABELS } from "@/lib/format";
import type { CurrentUser, RunRecord, RunStatus } from "@/lib/types";
import { useDriftAlerts } from "@/lib/useDriftAlerts";

import { useApp } from "./AppContext";
import { BellIcon } from "./icons";

/** Bước chờ Engineer (người tạo yêu cầu) và bước chờ Reviewer. */
export const ENGINEER_ACTION: RunStatus[] = [
  "waiting_input",
  "waiting_drift",
  "waiting_clarification",
  "waiting_plan_review",
  "waiting_schema",
  "waiting_rescue",
];
export const REVIEWER_ACTION: RunStatus[] = ["waiting_review"];
export const NEEDS_ACTION: RunStatus[] = [...ENGINEER_ACTION, ...REVIEWER_ACTION];

/** Lần chạy đang chờ CHÍNH người này theo vai trò: Engineer — yêu cầu của mình; Reviewer — hàng đợi duyệt. */
export function waitingFor(user: CurrentUser | null, runs: RunRecord[] | null): RunRecord[] {
  const list = runs ?? [];
  if (user?.role === "engineer")
    return list.filter((r) => ENGINEER_ACTION.includes(r.status) && r.requester === user.name);
  if (user?.role === "reviewer") return list.filter((r) => REVIEWER_ACTION.includes(r.status));
  return [];
}

export function runHref(run: RunRecord): string {
  return run.status === "waiting_review" ? `/runs/${run.id}/review` : `/runs/${run.id}`;
}

/** Đóng khung nổi khi bấm ra ngoài hoặc nhấn Esc. */
export function useDismiss(open: boolean, close: () => void) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const handle = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !box.current?.contains(event.target as Node))
        close();
    };
    document.addEventListener("mousedown", handle);
    document.addEventListener("keydown", handle);
    return () => {
      document.removeEventListener("mousedown", handle);
      document.removeEventListener("keydown", handle);
    };
  }, [open, close]);
  return box;
}

/** Chuông: các lần chạy đang chờ bạn (dữ liệu thật), không có thông báo dựng sẵn. */
export function NotificationBell() {
  const { runs, user } = useApp();
  const [open, setOpen] = useState(false);
  const box = useDismiss(open, () => setOpen(false));
  const waiting = waitingFor(user, runs);
  // Thay đổi cấu trúc nguồn mức "Chặn" đang mở: hiện bằng hình oval đỏ có số
  const { breaking } = useDriftAlerts();
  const total = breaking.length + waiting.length;

  return (
    <div className="popover" ref={box}>
      <button
        type="button"
        className="icon-btn"
        aria-label={`Thông báo: ${breaking.length} thay đổi cấu trúc chặn, ${waiting.length} lần chạy cần bạn`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <BellIcon />
        {total > 0 && <span className={`bell-count${breaking.length > 0 ? " danger" : ""}`}>{total}</span>}
      </button>
      {open && (
        <div className="flyout" role="dialog" aria-label="Thông báo">
          {breaking.length > 0 && (
            <>
              <div className="flyout-head">
                <strong>Thay đổi cấu trúc nguồn</strong>
                <span className="count-oval small">{breaking.length}</span>
              </div>
              <ul className="flyout-list">
                {breaking.slice(0, 6).map((c) => (
                  <li key={c.id}>
                    <Link href="/schema-changes" onClick={() => setOpen(false)}>
                      <strong className="truncate">
                        {c.table}: {CHANGE_LABELS[c.change_type] ?? c.change_type}
                      </strong>
                      <span className="small muted truncate">{c.detail}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
          <div className="flyout-head">
            <strong>Cần bạn xử lý</strong>
            <span className="muted small">{waiting.length}</span>
          </div>
          {waiting.length === 0 ? (
            <p className="empty">Không có gì đang chờ bạn.</p>
          ) : (
            <ul className="flyout-list">
              {waiting.slice(0, 12).map((run) => (
                <li key={run.id}>
                  <Link href={runHref(run)} onClick={() => setOpen(false)}>
                    <strong className="truncate">{run.summary.target ?? run.request_text}</strong>
                    <span className="small muted">{STATUS_LABELS[run.status]}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
