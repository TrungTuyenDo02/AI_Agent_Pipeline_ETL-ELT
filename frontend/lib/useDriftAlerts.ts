"use client";

import { useEffect } from "react";

import { useApp } from "@/components/AppContext";

import type { SchemaChange } from "./types";
import { usePoll } from "./usePoll";

// Thay đổi cấu trúc nguồn mức "Chặn" đang mở: chuông, tab điều hướng và trang Thay đổi cấu trúc dùng chung.
export const DRIFT_REFRESH_EVENT = "drift:refresh";

/** Báo cho mọi nơi đang hiện số đỏ tải lại ngay (gọi sau khi xác nhận hoặc kiểm tra lại cấu trúc). */
export function notifyDriftChanged(): void {
  window.dispatchEvent(new Event(DRIFT_REFRESH_EVENT));
}

export function useDriftAlerts(): { breaking: SchemaChange[]; sources: number } {
  // Chỉ hỏi khi đã có phiên: AppShell gọi hook này cả ở trang công khai (đăng nhập, /demo) — chưa đăng nhập thì
  // chỉ nhận 401, còn ở /demo thì lần hỏi đầu có thể chạy trước khi chế độ khách kịp bật.
  const { auth } = useApp();
  const { data, refresh } = usePoll<SchemaChange[]>(
    auth === "in" ? "/schema-changes?status=open&severity=breaking" : null,
    30000,
  );
  useEffect(() => {
    window.addEventListener(DRIFT_REFRESH_EVENT, refresh);
    return () => window.removeEventListener(DRIFT_REFRESH_EVENT, refresh);
  }, [refresh]);
  const breaking = data ?? [];
  return { breaking, sources: new Set(breaking.map((c) => c.source_id)).size };
}
