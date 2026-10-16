"use client";

import { useEffect } from "react";

import type { SchemaChange } from "./types";
import { usePoll } from "./usePoll";

// Thay đổi cấu trúc nguồn mức "Chặn" đang mở: chuông, tab điều hướng và trang Thay đổi cấu trúc dùng chung.
export const DRIFT_REFRESH_EVENT = "drift:refresh";

/** Báo cho mọi nơi đang hiện số đỏ tải lại ngay (gọi sau khi xác nhận hoặc kiểm tra lại cấu trúc). */
export function notifyDriftChanged(): void {
  window.dispatchEvent(new Event(DRIFT_REFRESH_EVENT));
}

export function useDriftAlerts(): { breaking: SchemaChange[]; sources: number } {
  const { data, refresh } = usePoll<SchemaChange[]>("/schema-changes?status=open&severity=breaking", 30000);
  useEffect(() => {
    window.addEventListener(DRIFT_REFRESH_EVENT, refresh);
    return () => window.removeEventListener(DRIFT_REFRESH_EVENT, refresh);
  }, [refresh]);
  const breaking = data ?? [];
  return { breaking, sources: new Set(breaking.map((c) => c.source_id)).size };
}
