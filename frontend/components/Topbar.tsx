"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Link from "next/link";

import { API_URL } from "@/lib/api";
import type { Role } from "@/lib/types";

import { THEME_LABELS, THEME_ORDER, useApp } from "./AppContext";
import { ArrowUpRightIcon, CheckIcon, DocIcon, Icon, LogoutIcon } from "./icons";
import { useDismiss, waitingFor } from "./NotificationBell";

export const ROLE_LABELS: Record<Role, string> = { engineer: "Engineer", reviewer: "Reviewer", admin: "Admin" };

/** Nút sáng/tối hiển thị sẵn trên thanh trên: bấm đổi ngay (lựa chọn lưu ở trình duyệt; "Theo máy" vẫn chọn được trong menu). */
export function ThemeToggle() {
  const { dark, setTheme } = useApp();
  const next = dark ? "light" : "dark";
  const label = dark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối";
  return (
    <button type="button" className="icon-btn theme-toggle" aria-label={label} title={label} onClick={() => setTheme(next)}>
      <Icon name={dark ? "light" : "dark"} size={20} weight="fill" />
    </button>
  );
}

export function ModeBadges() {
  const { status, statusError } = useApp();
  if (statusError) return <span className="badge danger">Mất kết nối API</span>;
  if (!status) return <span className="badge muted">Đang kiểm tra API…</span>;
  return status.simulated ? (
    <span className="badge warn" title="LLM_PROVIDER=mock: câu trả lời LLM là cố định, không phải chất lượng thật">
      Mô phỏng
    </span>
  ) : (
    <span className="badge ok" title={status.models}>
      LLM thật · {status.llm_provider}
    </span>
  );
}

/** Avatar tròn (chữ cái đầu): bấm mở menu người dùng (vai trò, đăng xuất) + giao diện + chế độ LLM. */
export function AvatarMenu() {
  const { user, logout, theme, setTheme } = useApp();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const box = useDismiss(open, () => setOpen(false));
  if (!user) return null;
  const initials = user.name.slice(0, 2).toUpperCase();

  async function signOut() {
    setLeaving(true);
    await logout();
    router.replace("/login");
  }

  return (
    <div className="popover" ref={box}>
      <button
        type="button"
        className="avatar"
        aria-label={`${user.display_name} (${ROLE_LABELS[user.role]}): mở menu`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {initials}
      </button>
      {open && (
        <div className="flyout menu" role="dialog" aria-label="Người dùng và giao diện">
          <div className="who">
            <strong>{user.display_name}</strong>
            <span className="muted small">@{user.name}</span>
            <span className={`badge role-${user.role}`}>{ROLE_LABELS[user.role]}</span>
          </div>
          <div className="segmented" role="group" aria-label="Giao diện">
            {THEME_ORDER.map((value) => (
              <button key={value} type="button" aria-pressed={theme === value} onClick={() => setTheme(value)}>
                {THEME_LABELS[value]}
              </button>
            ))}
          </div>
          <ModeBadges />
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer" className="menu-link">
            <DocIcon size={16} /> Tài liệu API <ArrowUpRightIcon size={14} />
          </a>
          <button type="button" className="btn logout-btn" onClick={signOut} disabled={leaving}>
            <LogoutIcon size={16} />
            {leaving ? "Đang đăng xuất…" : "Đăng xuất"}
          </button>
        </div>
      )}
    </div>
  );
}

/** Nhắc khi bước này dành cho vai trò khác (nút tương ứng bị khóa; backend vẫn trả 403 nếu cố gọi). */
export function RoleNote({ need }: { need: Role }) {
  const { user } = useApp();
  if (!user || user.role === need) return null;
  return (
    <div className="alert info">
      <span>
        Bước này dành cho vai trò {ROLE_LABELS[need]}. Bạn đang đăng nhập với vai trò {ROLE_LABELS[user.role]}.
      </span>
    </div>
  );
}

const SWITCHABLE: Role[] = ["engineer", "reviewer"];

/**
 * Huy hiệu vai trò = menu thả xuống đổi vai (CLAUDE.md yêu cầu 4). Vai trò gắn với TÀI KHOẢN và do máy chủ kiểm quyền,
 * nên đổi vai = đăng nhập tài khoản có vai đó (giao diện không tự cấp quyền). Reviewer thấy ngay số yêu cầu chờ duyệt.
 */
export function RoleChip() {
  const { user, runs, logout } = useApp();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState<Role | null>(null);
  const box = useDismiss(open, () => {
    setOpen(false);
    setTarget(null);
  });
  if (!user) return null;
  const queue = user.role === "reviewer" ? waitingFor(user, runs).length : 0;
  const roles = SWITCHABLE.includes(user.role) ? SWITCHABLE : [user.role, ...SWITCHABLE];

  async function switchTo() {
    await logout();
    router.replace("/login?next=/");
  }

  return (
    <div className="popover" ref={box}>
      <button
        type="button"
        className={`role-chip role-${user.role}`}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        title={`Bạn đang làm việc với vai trò ${ROLE_LABELS[user.role]}. Bấm để đổi vai`}
      >
        <span className="role-dot" aria-hidden />
        {ROLE_LABELS[user.role]}
        {queue > 0 && <span className="role-count">{queue} chờ duyệt</span>}
        <Icon name="caret" size={12} weight="bold" className="role-caret" />
      </button>
      {open && (
        <div className="flyout menu role-menu" role="dialog" aria-label="Đổi vai trò">
          <p className="small muted">Vai trò</p>
          <ul className="role-options">
            {roles.map((role) => (
              <li key={role}>
                <button
                  type="button"
                  className="role-option"
                  aria-pressed={role === user.role}
                  onClick={() => setTarget(role === user.role ? null : role)}
                >
                  <span className={`role-dot role-${role}`} aria-hidden />
                  {ROLE_LABELS[role]}
                  {role === user.role && (
                    <span className="role-current">
                      <CheckIcon size={14} /> đang dùng
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          {user.role === "reviewer" && (
            <Link href="/#queue" className="menu-link" onClick={() => setOpen(false)}>
              {queue > 0 ? `${queue} yêu cầu chờ duyệt` : "Không có yêu cầu chờ duyệt"}
            </Link>
          )}
          {target && (
            <div className="alert info role-switch">
              <span>
                Vai trò gắn với tài khoản. Để làm việc với vai trò {ROLE_LABELS[target]}, đăng nhập bằng tài khoản{" "}
                {ROLE_LABELS[target]}.
              </span>
              <button type="button" className="btn small" onClick={switchTo}>
                Đăng nhập tài khoản {ROLE_LABELS[target]}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
