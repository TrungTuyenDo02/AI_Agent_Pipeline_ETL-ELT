"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { plainStepLabel } from "@/lib/format";
import {
  buildCompactLog,
  buildTechnicalLog,
  hasRawEvents,
  LEVEL_LABELS,
  logAsText,
  logClock,
  type LogLevel,
} from "@/lib/runLog";
import type { RunDetail } from "@/lib/types";

import { CopyIcon, TerminalIcon } from "../icons";

type Filter = "all" | "warn" | "error";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "Tất cả" },
  { id: "warn", label: "Cảnh báo" },
  { id: "error", label: "Lỗi" },
];

const passes = (level: LogLevel, filter: Filter) =>
  filter === "all" || (filter === "error" ? level === "error" : level === "warn" || level === "error");

/** Tên bước đang chạy / trạng thái chung cho thanh tiêu đề. */
function headline(detail: RunDetail): string {
  if (detail.busy && detail.current) return "Đang chạy: " + plainStepLabel(detail.current.label);
  const human = (detail.stages ?? []).find((s) => s.state === "human");
  if (human) return "Đang chờ người: " + human.label;
  if (detail.record.status === "failed") return "Đã dừng vì lỗi";
  if (detail.record.status === "approved") return "Đã xong, code đã duyệt";
  return "Đang nghỉ";
}

/** CLAUDE.md yêu cầu 2: panel "Nhật ký chạy" kiểu terminal, chế độ gọn cho người không chuyên. */
export function RunLog({ detail }: { detail: RunDetail }) {
  const [technical, setTechnical] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const screen = useRef<HTMLDivElement>(null);

  const all = useMemo(() => (technical ? buildTechnicalLog(detail) : buildCompactLog(detail)), [detail, technical]);
  const lines = useMemo(() => {
    const q = query.trim().toLowerCase();
    return all.filter(
      (l) => passes(l.level, filter) && (!q || `${l.step} ${l.text} ${l.hint ?? ""}`.toLowerCase().includes(q)),
    );
  }, [all, filter, query]);
  const counts = {
    warn: all.filter((l) => l.level === "warn").length,
    error: all.filter((l) => l.level === "error").length,
  };

  useEffect(() => {
    if (autoScroll && screen.current) screen.current.scrollTop = screen.current.scrollHeight;
  }, [autoScroll, lines.length, detail.current?.node]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(logAsText(lines));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // trình duyệt chặn clipboard: bỏ qua
    }
  }

  function download() {
    const blob = new Blob([logAsText(all)], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `nhat-ky-${detail.record.id}${technical ? "-ky-thuat" : ""}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="card run-log" aria-labelledby="run-log-title">
      <header className="run-log-head">
        <div className="run-log-title">
          <TerminalIcon size={16} />
          <h2 id="run-log-title">Nhật ký chạy</h2>
          <span className="run-log-now">
            {detail.busy && <span className="dot ok pulse" aria-hidden />}
            {headline(detail)}
          </span>
        </div>
        <div className="run-log-actions">
          <button type="button" className="btn small" onClick={copy} disabled={lines.length === 0}>
            <CopyIcon size={13} /> {copied ? "Đã sao chép" : "Sao chép"}
          </button>
          <button type="button" className="btn small" onClick={download} disabled={all.length === 0}>
            Tải log
          </button>
          <button
            type="button"
            className="btn small"
            aria-pressed={autoScroll}
            onClick={() => setAutoScroll((v) => !v)}
            title="Tự cuộn xuống dòng mới nhất khi đang chạy"
          >
            Tự cuộn: {autoScroll ? "bật" : "tắt"}
          </button>
        </div>
      </header>

      <div className="run-log-tools">
        <div className="segmented" role="group" aria-label="Lọc theo mức độ">
          {FILTERS.map((f) => (
            <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>
              {f.label}
              {f.id !== "all" && counts[f.id] > 0 ? ` (${counts[f.id]})` : ""}
            </button>
          ))}
        </div>
        <input
          type="search"
          className="run-log-search"
          placeholder="Tìm trong nhật ký…"
          aria-label="Tìm trong nhật ký"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="run-log-switch">
          <input type="checkbox" checked={technical} onChange={(e) => setTechnical(e.target.checked)} />
          Xem chi tiết kỹ thuật
        </label>
      </div>

      {technical && !hasRawEvents(detail) && (
        <p className="small muted run-log-note">
          Máy chủ đã khởi động lại nên không còn log gốc của lần chạy này; dưới đây là trạng thái từng bước đã lưu.
        </p>
      )}

      <div className="run-log-screen" ref={screen} role="log" aria-live="polite" aria-label="Các dòng nhật ký">
        {lines.length === 0 && (
          <div className="log-line">
            <span className="log-text log-empty">
              {all.length === 0 ? "Chưa có dòng nhật ký nào." : "Không có dòng nào khớp bộ lọc."}
            </span>
          </div>
        )}
        {lines.map((line) => (
          <div key={line.id} className={`log-line level-${line.level}`}>
            <span className="log-time">{logClock(line.time)}</span>
            <span className={`log-level level-${line.level}`}>{LEVEL_LABELS[line.level]}</span>
            <span className="log-text">
              <span className="log-step" title={line.code ? `Mã bước: ${line.code}` : undefined}>
                {line.step}
              </span>{" "}
              · {line.text}
              {line.hint && <span className="log-hint">→ {line.hint}</span>}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
