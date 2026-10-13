"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ComponentType, type ReactNode, type SVGProps } from "react";

import { useApp } from "./AppContext";
import type { Role } from "@/lib/types";

import { BookIcon, DatabaseIcon, HomeIcon, ListIcon, SparkIcon, UsersIcon } from "./icons";
import { NotificationBell } from "./NotificationBell";
import { RunSearch } from "./RunSearch";
import { AvatarMenu, ModeBadges, RoleChip } from "./Topbar";

// Bố cục: thanh trên (logo · tab · tìm · vai trò · chuông · avatar), thẻ trắng trên nền phẳng. Không còn thanh icon dọc
// (trùng menu trên; đổi giao diện và tài liệu API nằm trong menu avatar) — CLAUDE.md yêu cầu 4.
type IconType = ComponentType<SVGProps<SVGSVGElement> & { size?: number }>;
type NavItem = { href: string; label: string; icon: IconType };
const HOME: NavItem = { href: "/", label: "Trang chủ", icon: HomeIcon };
const RUNS: NavItem = { href: "/runs", label: "Lần chạy", icon: ListIcon };
const SOURCES: NavItem = { href: "/catalog", label: "Dữ liệu nguồn", icon: DatabaseIcon };
const ERRORS: NavItem = { href: "/errors", label: "Sổ lỗi", icon: BookIcon };
// Mỗi vai trò thấy trước việc của mình (ẩn mục chỉ để gọn; quyền thật kiểm ở backend).
const NAV: Record<Role, NavItem[]> = {
  engineer: [HOME, RUNS, SOURCES, ERRORS],
  reviewer: [{ ...HOME, label: "Hàng đợi" }, RUNS, ERRORS, SOURCES],
  admin: [HOME, { href: "/admin", label: "Người dùng", icon: UsersIcon }, RUNS, SOURCES],
};
function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function TopBar() {
  const pathname = usePathname();
  const { user } = useApp();
  const nav = NAV[user?.role ?? "engineer"];
  return (
    <header className="topbar">
      <Link href="/" className="brand">
        <SparkIcon size={22} className="brand-spark" />
        <span>P-113 Agent Studio</span>
      </Link>
      <nav className="nav-pills" aria-label="Điều hướng chính">
        {nav.map(({ href, label, icon: Glyph }) => (
          <Link
            key={href}
            href={href}
            className={isActive(pathname, href) ? "nav-pill active" : "nav-pill"}
            aria-current={isActive(pathname, href) ? "page" : undefined}
          >
            <Glyph size={16} />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
      <div className="topbar-tools">
        <RunSearch />
        <RoleChip />
        <NotificationBell />
        <AvatarMenu />
      </div>
    </header>
  );
}

function Footer() {
  const { status, statusError } = useApp();
  return (
    <footer className="footer">
      <span className="row">
        <span className={statusError ? "dot fail" : status ? "dot ok" : "dot"} aria-hidden />
        {statusError ? "Mất kết nối API" : status ? (status.agent ?? "API") : "Đang kiểm tra API…"}
      </span>
      <ModeBadges />
    </footer>
  );
}

/** Màn chờ khi đang kiểm phiên hoặc đang chuyển sang trang đăng nhập. */
function Splash({ text }: { text: string }) {
  return (
    <div className="splash" role="status" aria-live="polite">
      <SparkIcon size={28} className="brand-spark" />
      <span>{text}</span>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { auth, user } = useApp();
  const onLogin = pathname.startsWith("/login");

  // Mọi trang (trừ đăng nhập) cần phiên; hết phiên → về đăng nhập, quay lại đúng trang sau khi đăng nhập
  useEffect(() => {
    if (auth === "out" && !onLogin) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [auth, onLogin, pathname, router]);

  if (onLogin) return <>{children}</>;
  if (auth !== "in") {
    return (
      <div className="page">
        <Splash text={auth === "checking" ? "Đang kiểm tra phiên đăng nhập…" : "Đang chuyển tới trang đăng nhập…"} />
      </div>
    );
  }
  return (
    <div className="page" data-role={user?.role}>
      <a href="#main" className="skip-link">
        Bỏ qua tới nội dung
      </a>
      <div className="frame">
        <TopBar />
        <div className="body">
          <main id="main" className="content">
            {children}
          </main>
        </div>
        <Footer />
      </div>
    </div>
  );
}
