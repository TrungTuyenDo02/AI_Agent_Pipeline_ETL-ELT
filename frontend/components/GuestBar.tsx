"use client";

// Chế độ khách: dải cố định trong thanh trên (huy hiệu + chú thích + đổi vai + làm lại + đăng nhập) và nhãn "số liệu mẫu"
// đặt cạnh mọi số thời gian/chi phí. Chỉ hiện khi đang là khách; đăng nhập thường không thấy gì khác.

import Link from "next/link";
import { useState } from "react";

import { GUEST_NOTE, type GuestRole } from "@/lib/guest";

import { useApp } from "./AppContext";
import { ConfirmDialog } from "./ConfirmDialog";
import { Icon } from "./icons";
import { ROLE_LABELS } from "./Topbar";

const GUEST_ROLES: GuestRole[] = ["engineer", "reviewer"];

export function GuestStrip() {
  const { guest, user, switchGuestRole, resetGuest, exitGuest } = useApp();
  const [confirm, setConfirm] = useState(false);
  if (!guest) return null;
  return (
    <div className="guest-strip" role="region" aria-label="Chế độ khách">
      <span className="guest-badge">
        <Icon name="show" size={14} weight="bold" /> Chế độ khách · Dữ liệu mẫu
      </span>
      <span className="guest-note">{GUEST_NOTE}</span>
      <div className="guest-actions">
        <div className="segmented" role="group" aria-label="Vai trò dùng thử">
          {GUEST_ROLES.map((role) => (
            <button
              key={role}
              type="button"
              aria-pressed={user?.role === role}
              onClick={() => switchGuestRole(role)}
              title={`Xem với vai trò ${ROLE_LABELS[role]}`}
            >
              {ROLE_LABELS[role]}
            </button>
          ))}
        </div>
        <Link href="/docs" className="btn small">
          Giới thiệu
        </Link>
        <button type="button" className="btn small" onClick={() => setConfirm(true)}>
          Làm lại từ đầu
        </button>
        <button type="button" className="btn small primary" onClick={() => exitGuest("/login")}>
          Đăng nhập
        </button>
      </div>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Làm lại từ đầu?"
        icon="reload"
        confirmLabel="Làm lại từ đầu"
        confirmClass="btn primary"
        onConfirm={resetGuest}
      >
        <p>
          Mọi thao tác bạn đã làm trên dữ liệu mẫu (yêu cầu mới, câu trả lời, duyệt) sẽ bị xóa và bộ mẫu được dựng lại.
        </p>
      </ConfirmDialog>
    </div>
  );
}

/** Nhãn "số liệu mẫu" cạnh số thời gian/chi phí; chỉ hiện ở chế độ khách. */
export function SampleTag() {
  const { guest } = useApp();
  if (!guest) return null;
  return (
    <span className="badge warn sample-tag" title="Số thời gian, token và chi phí trong chế độ khách là số liệu mẫu">
      số liệu mẫu
    </span>
  );
}
