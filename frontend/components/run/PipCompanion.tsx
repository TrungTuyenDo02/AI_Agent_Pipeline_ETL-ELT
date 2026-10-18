"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState, useSyncExternalStore, type PointerEvent } from "react";
import { createPortal } from "react-dom";

import { pipState, type PipState } from "@/lib/pip";
import type { RunDetail } from "@/lib/types";

import { Icon } from "../icons";
import { PipSprite } from "../PipSprite";

type Corner = "bottom-right" | "bottom-left" | "top-right" | "top-left";
interface Preferences {
  corner: Corner;
  hidden: boolean;
}
interface Drag {
  x: number;
  y: number;
}
const STORAGE_KEY = "p113.pip.position";
const CORNERS: { value: Corner; label: string }[] = [
  { value: "top-left", label: "Góc trên trái" },
  { value: "top-right", label: "Góc trên phải" },
  { value: "bottom-left", label: "Góc dưới trái" },
  { value: "bottom-right", label: "Góc dưới phải" },
];
const DEFAULTS: Preferences = { corner: "bottom-right", hidden: false };
const subscribe = () => () => {};
const clientReady = () => true;
const serverReady = () => false;

function readPreferences(): Preferences {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (saved && CORNERS.some((corner) => corner.value === saved.corner)) {
      return { corner: saved.corner, hidden: saved.hidden === true };
    }
  } catch {
    /* The companion remains usable when storage is unavailable. */
  }
  return DEFAULTS;
}

/** A viewport companion: only the cat is persistent; its speech bubble is temporary. */
export function PipCompanion({ detail, guest }: { detail?: RunDetail; guest: boolean }) {
  const ready = useSyncExternalStore(subscribe, clientReady, serverReady);
  const [preferences, setPreferences] = useState(readPreferences);
  const [manualOpen, setManualOpen] = useState(false);
  const [dismissedNotice, setDismissedNotice] = useState("");
  const [drag, setDrag] = useState<Drag | null>(null);
  const host = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const gesture = useRef<{
    id: number;
    startX: number;
    startY: number;
    left: number;
    top: number;
    moved: boolean;
  } | null>(null);
  const dragged = useRef(false);
  const bubbleId = useId();
  const state: PipState = detail
    ? pipState(detail)
    : {
        pose: "idle",
        title: "Pip ở đây cùng bạn!",
        message: guest
          ? "Bạn có thể thử tạo yêu cầu hoặc mở một lần chạy mẫu. Pip sẽ đổi hành động theo từng bước mô phỏng."
          : "Mô tả pipeline bạn cần hoặc mở một lần chạy. Pip sẽ đồng hành cùng bạn qua từng bước.",
      };
  const status = detail?.record.status;
  const needsInput = Boolean(
    detail && !detail.busy && status !== "running" && status !== "paused" && status !== "approved",
  );
  const noticeKey = detail ? `${detail.record.id}:${status}` : "welcome";
  const announce = needsInput || status === "approved";
  const open = manualOpen || (announce && dismissedNotice !== noticeKey);
  const canPatrol = Boolean(detail && (detail.busy || status === "running") && !detail.record.pause_requested);
  const review = status === "waiting_review" || status === "approved";
  const href = detail
    ? `/runs/${encodeURIComponent(detail.record.id)}${review ? "/review" : "#run-workspace"}`
    : "/runs";

  function save(change: Partial<Preferences>) {
    const next = { ...preferences, ...change };
    setPreferences(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* Session state still works. */
    }
  }

  function closeBubble(focus = false) {
    setManualOpen(false);
    setDismissedNotice(noticeKey);
    if (focus) trigger.current?.focus();
  }

  useEffect(() => {
    if (!announce || preferences.hidden) return;
    const timer = window.setTimeout(() => setDismissedNotice(noticeKey), status === "approved" ? 5000 : 9000);
    return () => window.clearTimeout(timer);
  }, [announce, noticeKey, preferences.hidden, status]);

  useEffect(() => {
    if (!open || preferences.hidden) return;
    function outside(event: globalThis.PointerEvent) {
      if (!host.current?.contains(event.target as Node)) {
        setManualOpen(false);
        setDismissedNotice(noticeKey);
      }
    }
    function escape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      const focusInside = host.current?.contains(document.activeElement);
      setManualOpen(false);
      setDismissedNotice(noticeKey);
      if (focusInside) trigger.current?.focus();
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open, preferences.hidden, noticeKey]);

  function startDrag(event: PointerEvent<HTMLButtonElement>) {
    dragged.current = false;
    if (event.button !== 0 || !event.isPrimary || matchMedia("(max-width: 639px)").matches) return;
    const rect = event.currentTarget.getBoundingClientRect();
    gesture.current = {
      id: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      left: rect.left,
      top: rect.top,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveDrag(event: PointerEvent<HTMLButtonElement>) {
    const current = gesture.current;
    if (!current || current.id !== event.pointerId) return;
    const dx = event.clientX - current.startX,
      dy = event.clientY - current.startY;
    if (!current.moved && Math.hypot(dx, dy) < 6) return;
    current.moved = true;
    dragged.current = true;
    closeBubble();
    setDrag({
      x: Math.max(16, Math.min(innerWidth - 104, current.left + dx)),
      y: Math.max(88, Math.min(innerHeight - 104, current.top + dy)),
    });
  }

  function endDrag(event: PointerEvent<HTMLButtonElement>, cancelled = false) {
    const current = gesture.current;
    if (!current || current.id !== event.pointerId) return;
    if (current.moved && !cancelled) {
      const corner: Corner = `${event.clientY < innerHeight / 2 ? "top" : "bottom"}-${event.clientX < innerWidth / 2 ? "left" : "right"}`;
      save({ corner });
    }
    gesture.current = null;
    setDrag(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId))
      event.currentTarget.releasePointerCapture(event.pointerId);
  }

  if (!ready) return null;
  return createPortal(
    <aside
      ref={host}
      className="pip-companion"
      data-pip-state={state.pose}
      data-corner={preferences.corner}
      data-open={open && !preferences.hidden}
      data-dragging={Boolean(drag)}
      data-patrol={canPatrol && !open && !preferences.hidden && !drag}
      style={drag ? { left: drag.x, top: drag.y, right: "auto", bottom: "auto" } : undefined}
      aria-label="Linh vật Pip đồng hành"
    >
      {preferences.hidden ? (
        <button
          type="button"
          className="pip-restore"
          title="Hiện Pip"
          onClick={() => {
            save({ hidden: false });
            setManualOpen(true);
          }}
        >
          <PipSprite size={40} />
          <span className="sr-only">Hiện Pip</span>
        </button>
      ) : (
        <>
          <div className="pip-perch">
            <button
              ref={trigger}
              type="button"
              className="pip-cat"
              aria-label={`Pip: ${state.title}. Bấm để xem trạng thái và tùy chọn`}
              aria-expanded={open}
              aria-controls={open ? bubbleId : undefined}
              title="Bấm để trò chuyện với Pip · Kéo để đổi góc"
              onPointerDown={startDrag}
              onPointerMove={moveDrag}
              onPointerUp={(event) => endDrag(event)}
              onPointerCancel={(event) => endDrag(event, true)}
              onLostPointerCapture={() => {
                gesture.current = null;
                setDrag(null);
              }}
              onClick={() => {
                if (dragged.current) {
                  dragged.current = false;
                  return;
                }
                if (open) closeBubble();
                else setManualOpen(true);
              }}
            >
              <span className="pip-at-home">
                <PipSprite key={state.pose} pose={state.pose} size={88} animated />
              </span>
              <span className="pip-walking" aria-hidden="true">
                <span className="pip-walk-sprite" />
              </span>
              {needsInput && <span className="pip-attention" aria-hidden="true" />}
            </button>
          </div>
          {open && (
            <div id={bubbleId} className="pip-bubble">
              <button
                type="button"
                className="icon-btn pip-bubble-close"
                onClick={() => closeBubble(true)}
                aria-label="Đóng lời nhắn của Pip"
              >
                <Icon name="close" size={16} />
              </button>
              <div role="status" aria-live="polite" aria-atomic="true">
                <strong>{state.title}</strong>
                <p>
                  {guest && state.pose === "done"
                    ? "Bạn đã đi hết quy trình mô phỏng. Bạn có thể xem lại code mẫu."
                    : state.message}
                </p>
                {guest && <span className="small muted">Chế độ khách · Dữ liệu mẫu</span>}
              </div>
              <Link className="pip-action" href={href} onClick={() => closeBubble()}>
                {!detail
                  ? "Xem các lần chạy"
                  : review
                    ? "Xem code và bằng chứng"
                    : needsInput
                      ? "Xem phần cần xử lý"
                      : "Xem tiến trình"}{" "}
                <span aria-hidden="true">→</span>
              </Link>
              <div className="pip-corners" role="group" aria-label="Vị trí Pip trên màn hình">
                {CORNERS.map((corner) => (
                  <button
                    key={corner.value}
                    type="button"
                    aria-label={corner.label}
                    title={corner.label}
                    aria-pressed={preferences.corner === corner.value}
                    data-corner={corner.value}
                    onClick={() => save({ corner: corner.value })}
                  >
                    <span aria-hidden="true" />
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="pip-hide"
                onClick={() => {
                  save({ hidden: true });
                  closeBubble();
                }}
              >
                Ẩn Pip
              </button>
            </div>
          )}
        </>
      )}
    </aside>,
    document.body,
  );
}
