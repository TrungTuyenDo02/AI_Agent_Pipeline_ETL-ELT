"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useApp } from "./AppContext";
import { Icon } from "./icons";
import { runHref, useDismiss } from "./NotificationBell";
import { StatusPill } from "./StatusPill";

/** Tìm lần chạy theo yêu cầu, bảng đích hoặc mã (trên danh sách thật đã tải). */
export function RunSearch() {
  const { runs } = useApp();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const box = useDismiss(open, () => setOpen(false));
  const input = useRef<HTMLInputElement>(null);

  // Cmd + K (máy Mac) hoặc Ctrl + K: nhảy vào ô tìm từ bất kỳ đâu (CLAUDE.md 9.2)
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        input.current?.focus();
        input.current?.select();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const needle = query.trim().toLowerCase();
  const found = needle
    ? (runs ?? [])
        .filter((run) =>
          [run.request_text, run.summary.target ?? "", run.id].some((text) => text.toLowerCase().includes(needle)),
        )
        .slice(0, 8)
    : [];
  return (
    <div className="popover search" ref={box}>
      <label className="search-box" title="Tìm lần chạy (Ctrl + K hoặc Cmd + K)">
        <Icon name="search" size={16} />
        <span className="sr-only">Tìm lần chạy</span>
        <input
          ref={input}
          type="search"
          aria-keyshortcuts="Control+K Meta+K"
          placeholder="Tìm lần chạy…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
        />
        <kbd aria-hidden>Ctrl K</kbd>
      </label>
      {open && needle && (
        <div className="flyout" role="dialog" aria-label="Kết quả tìm">
          {found.length === 0 ? (
            <p className="empty">Không thấy lần chạy nào.</p>
          ) : (
            <ul className="flyout-list">
              {found.map((run) => (
                <li key={run.id}>
                  <Link
                    href={runHref(run)}
                    onClick={() => {
                      setOpen(false);
                      setQuery("");
                    }}
                  >
                    <strong className="truncate">{run.summary.target ?? run.request_text}</strong>
                    <span className="row small">
                      <StatusPill status={run.status} />
                      <span className="muted truncate">{run.request_text}</span>
                    </span>
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
