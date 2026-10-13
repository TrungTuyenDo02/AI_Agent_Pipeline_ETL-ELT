"use client";

// Thông báo nhanh (toast) cho kết quả một thao tác (CLAUDE.md 9.9): góc dưới phải, tự ẩn sau vài giây,
// không chặn màn hình. Lỗi của một form vẫn hiện ngay dưới form đó (gần chỗ người dùng đang nhìn).

import { AnimatePresence, motion } from "framer-motion";
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

import { Icon, StatusIcon } from "./icons";

type ToastTone = "ok" | "danger" | "info";

interface ToastItem {
  id: number;
  tone: ToastTone;
  text: string;
}

type Notify = (text: string, tone?: ToastTone) => void;

const ToastContext = createContext<Notify>(() => {});

const SHOW_MS = 4500;
const MAX_SHOWN = 3;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setItems((all) => all.filter((t) => t.id !== id)), []);

  const notify = useCallback<Notify>(
    (text, tone = "ok") => {
      const id = nextId.current++;
      setItems((all) => [...all.slice(-(MAX_SHOWN - 1)), { id, tone, text }]);
      setTimeout(() => dismiss(id), tone === "danger" ? SHOW_MS * 2 : SHOW_MS);
    },
    [dismiss],
  );

  const value = useMemo(() => notify, [notify]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* aria-live: trình đọc màn hình đọc thông báo mới mà không chuyển focus */}
      <div className="toast-stack" role="status" aria-live="polite">
        <AnimatePresence initial={false}>
          {items.map((t) => (
            <motion.div
              key={t.id}
              layout
              className={`toast ${t.tone}`}
              initial={{ opacity: 0, y: 16, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97, transition: { duration: 0.15 } }}
            >
              <StatusIcon tone={t.tone} size={20} />
              <span className="toast-text">{t.text}</span>
              <button
                type="button"
                className="toast-close"
                onClick={() => dismiss(t.id)}
                aria-label="Đóng thông báo"
                title="Đóng"
              >
                <Icon name="close" size={16} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

/** `toast("Đã gửi")`, `toast("Không gửi được", "danger")`. */
export function useToast(): Notify {
  return useContext(ToastContext);
}
