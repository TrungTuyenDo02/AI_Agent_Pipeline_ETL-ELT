// Thành phần giao diện nhỏ dùng chung: trạng thái tải, lỗi, nhãn trạng thái, thẻ.

import type { ReactNode } from "react";

import type { IconName } from "@/lib/icons";
import type { RunStatus } from "@/lib/types";

import { CheckIcon, Icon, StatusIcon } from "./icons";
import { StatusPill } from "./StatusPill";

const SKELETON_WIDTHS = ["92%", "76%", "84%", "60%", "70%"];

/** Đang tải: khung xám nhấp nháy giữ chỗ nội dung (CLAUDE.md 9.9) + một dòng chú thích việc đang làm. */
export function Loading({ text = "Đang tải…", lines = 3 }: { text?: string; lines?: number }) {
  return (
    <div className="loading-skeleton" role="status" aria-live="polite" aria-busy="true">
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className="skeleton" style={{ width: SKELETON_WIDTHS[i % SKELETON_WIDTHS.length] }} />
      ))}
      <span className="skeleton-caption">{text}</span>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="alert danger" role="alert">
      <span className="alert-text" style={{ whiteSpace: "pre-line" }}>
        <StatusIcon tone="danger" size={18} />
        {message}
      </span>
      {onRetry && (
        <button type="button" className="btn small" onClick={onRetry}>
          Thử lại
        </button>
      )}
    </div>
  );
}

/** Trạng thái lần chạy: dùng chung nhãn có icon + màu + chữ (CLAUDE.md 9.11). */
export function StatusBadge({ status }: { status: RunStatus }) {
  return <StatusPill status={status} />;
}

export function Card({ title, actions, children }: { title: ReactNode; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      <header className="card-head">
        <h2>{title}</h2>
        {actions}
      </header>
      <div className="card-body">{children}</div>
    </section>
  );
}

/** Rỗng. Có `icon` → trạng thái rỗng cả khung (icon duotone 56px, câu hướng dẫn, nút hành động); không có → một dòng chữ phụ. */
export function Empty({ children, icon, action }: { children: ReactNode; icon?: IconName; action?: ReactNode }) {
  if (!icon) return <p className="empty">{children}</p>;
  return (
    <div className="empty-state">
      <Icon name={icon} size={56} weight="duotone" />
      <p>{children}</p>
      {action}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="stat" title={hint}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function PassMark({ passed }: { passed: boolean | null }) {
  if (passed === null)
    return (
      <span className="mark info" role="img" aria-label="Thông tin">
        <StatusIcon tone="info" size={14} />
      </span>
    );
  return passed ? (
    <span className="mark ok" role="img" aria-label="Đạt">
      <StatusIcon tone="ok" size={14} />
    </span>
  ) : (
    <span className="mark danger" role="img" aria-label="Không đạt">
      <StatusIcon tone="danger" size={14} />
    </span>
  );
}

/** Thẻ một bước của luồng (bố cục Studio): số thứ tự tròn, tiêu đề, nhãn bên phải; `state` đổi màu số. */
export function StepCard({
  step,
  title,
  aside,
  state = "idle",
  children,
}: {
  step: ReactNode;
  title: ReactNode;
  aside?: ReactNode;
  state?: "idle" | "active" | "done" | "waiting";
  children: ReactNode;
}) {
  return (
    <section className="card step-card" data-state={state}>
      <header className="step-head">
        <div className="step-title">
          <span className="step-num" aria-hidden>
            {step}
          </span>
          <h2>{title}</h2>
        </div>
        {aside}
      </header>
      <div className="step-body">{children}</div>
    </section>
  );
}

/** Ô chọn kiểu "nút bóng" (ô vuông bo tròn, tô gradient khi chọn): vẫn là checkbox thật, bàn phím/đọc màn hình dùng được. */
export function Checkbox({
  checked,
  onChange,
  disabled,
  children,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="check" data-disabled={disabled || undefined}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="check-box" aria-hidden>
        <CheckIcon size={14} strokeWidth={3} />
      </span>
      <span className="check-label">{children}</span>
    </label>
  );
}
