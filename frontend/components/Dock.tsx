"use client";

// Dock nổi bên trái (CLAUDE.md 9.4) và thanh điều hướng dưới đáy trên điện thoại (9.2, 9.9).
// Dock: lối tắt Trang chủ · Tạo mới · Tài liệu · Giám sát · Cài đặt. Thanh dưới đáy (<640px): bốn mục điều hướng chính
// + Tạo mới, thay cho các tab trên thanh trên (bị ẩn ở màn nhỏ).

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { API_URL } from "@/lib/api";
import type { IconName } from "@/lib/icons";
import { runFilterHref } from "@/lib/runFilters";

import { THEME_LABELS, THEME_ORDER, useApp } from "./AppContext";
import { Icon } from "./icons";
import { useDismiss } from "./NotificationBell";

const MONITOR_HREF = runFilterHref("dang-chay");

export interface NavLinkItem {
  href: string;
  label: string;
  icon: IconName;
}

function DockLink({ href, label, icon, active }: NavLinkItem & { active: boolean }) {
  return (
    <Link
      href={href}
      className={active ? "dock-item active" : "dock-item"}
      aria-label={label}
      aria-current={active ? "page" : undefined}
      data-tip={label}
    >
      <Icon name={icon} size={22} weight={active ? "fill" : "regular"} />
    </Link>
  );
}

function SettingsButton() {
  const { theme, setTheme } = useApp();
  const [open, setOpen] = useState(false);
  const box = useDismiss(open, () => setOpen(false));
  return (
    <div className="popover dock-popover" ref={box}>
      <button
        type="button"
        className={open ? "dock-item active" : "dock-item"}
        aria-label="Cài đặt"
        aria-expanded={open}
        data-tip={open ? undefined : "Cài đặt"}
        onClick={() => setOpen(!open)}
      >
        <Icon name="settings" size={22} weight={open ? "fill" : "regular"} />
      </button>
      {open && (
        <div className="flyout menu dock-flyout" role="dialog" aria-label="Cài đặt">
          <strong>Cài đặt</strong>
          <p className="small muted">Giao diện</p>
          <div className="segmented" role="group" aria-label="Giao diện">
            {THEME_ORDER.map((value) => (
              <button key={value} type="button" aria-pressed={theme === value} onClick={() => setTheme(value)}>
                {THEME_LABELS[value]}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DockItems() {
  const pathname = usePathname();
  const filter = useSearchParams().get("loc");
  const { user } = useApp();
  const engineer = user?.role === "engineer";
  const monitoring = pathname === "/runs" && filter === "dang-chay";
  return (
    <>
      <DockLink href="/" label="Trang chủ" icon="home" active={pathname === "/"} />
      {/* Chỉ Engineer tạo yêu cầu (backend cũng kiểm) */}
      {engineer && <DockLink href="/#request" label="Tạo mới" icon="create" active={false} />}
      <DockLink href={MONITOR_HREF} label="Giám sát: lần chạy đang chạy" icon="monitor" active={monitoring} />
      <a
        href={`${API_URL}/docs`}
        target="_blank"
        rel="noreferrer"
        className="dock-item"
        aria-label="Tài liệu API (mở tab mới)"
        data-tip="Tài liệu API"
      >
        <Icon name="docs" size={22} />
      </a>
      <span className="dock-sep" aria-hidden />
      <SettingsButton />
    </>
  );
}

/** Dock nổi bên trái (≥ 640px). Kính mờ vì là lớp nổi; nội dung chính chừa lề trái cho dock. */
export function Dock() {
  return (
    <nav className="dock" aria-label="Lối tắt">
      <Suspense fallback={null}>
        <DockItems />
      </Suspense>
    </nav>
  );
}

/** Thanh dưới đáy (< 640px): điều hướng chính theo vai trò, thêm nút Tạo mới ở giữa cho Engineer. */
export function BottomNav({ items, isActive }: { items: NavLinkItem[]; isActive: (href: string) => boolean }) {
  const { user } = useApp();
  const engineer = user?.role === "engineer";
  const middle = Math.ceil(items.length / 2);
  const create: NavLinkItem = { href: "/#request", label: "Tạo mới", icon: "create" };
  const all = engineer ? [...items.slice(0, middle), create, ...items.slice(middle)] : items;
  return (
    <nav className="bottom-nav" aria-label="Điều hướng chính (điện thoại)">
      {all.map(({ href, label, icon }) => {
        const active = href !== create.href && isActive(href);
        return (
          <Link
            key={href}
            href={href}
            className={href === create.href ? "bottom-item create" : active ? "bottom-item active" : "bottom-item"}
            aria-current={active ? "page" : undefined}
          >
            <Icon name={icon} size={href === create.href ? 26 : 22} weight={active ? "fill" : "regular"} />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
