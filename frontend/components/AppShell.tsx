"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useApp } from "./AppContext";
import type { Role } from "@/lib/types";
import { useDriftAlerts } from "@/lib/useDriftAlerts";

import { BottomNav, Dock, type NavLinkItem } from "./Dock";
import { GuestStrip } from "./GuestBar";
import { GuideBanner } from "./guide/Guide";
import { Icon, SparkIcon } from "./icons";
import { NotificationBell } from "./NotificationBell";
import { RunSearch } from "./RunSearch";
import { AvatarMenu, ModeBadges, RoleChip, ThemeToggle } from "./Topbar";

// Bố cục (CLAUDE.md 9.4): thanh trên (logo · tab · tìm · vai trò · chuông · avatar), dock nổi bên trái (lối tắt),
// thẻ nền đặc trên nền phẳng. Điện thoại (< 640px): tab chuyển xuống thanh dưới đáy, ẩn dock.
type NavItem = NavLinkItem;
const HOME: NavItem = { href: "/", label: "Trang chủ", icon: "home" };
const RUNS: NavItem = { href: "/runs", label: "Lần chạy", icon: "runs" };
const SOURCES: NavItem = { href: "/catalog", label: "Dữ liệu nguồn", icon: "sources" };
const REGISTRY: NavItem = { href: "/sources", label: "Nguồn dữ liệu", icon: "registry" };
const ERRORS: NavItem = { href: "/errors", label: "Sổ lỗi", icon: "errors" };
const DRIFT: NavItem = { href: "/schema-changes", label: "Thay đổi cấu trúc", icon: "drift" };
// Mỗi vai trò thấy trước việc của mình (ẩn mục chỉ để gọn; quyền thật kiểm ở backend).
const NAV: Record<Role, NavItem[]> = {
  engineer: [HOME, RUNS, SOURCES, REGISTRY, DRIFT, ERRORS],
  reviewer: [{ ...HOME, label: "Hàng đợi" }, RUNS, ERRORS, SOURCES, REGISTRY, DRIFT],
  admin: [HOME, { href: "/admin", label: "Người dùng", icon: "users" }, RUNS, SOURCES, REGISTRY, DRIFT],
};
function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/** Gắn số đỏ: Thay đổi cấu trúc = số thay đổi chặn đang mở; Nguồn dữ liệu = số nguồn đang có thay đổi chặn. */
function useNavItems(role: Role): NavItem[] {
  const { breaking, sources } = useDriftAlerts();
  const badges: Record<string, number> = { [DRIFT.href]: breaking.length, [REGISTRY.href]: sources };
  return NAV[role].map((item) => ({ ...item, badge: badges[item.href] || undefined }));
}

function TopBar() {
  const pathname = usePathname();
  const { user } = useApp();
  const nav = useNavItems(user?.role ?? "engineer");
  return (
    <header className="topbar">
      <Link href="/" className="brand">
        <SparkIcon size={22} className="brand-spark" />
        <span>P-113 Agent Studio</span>
      </Link>
      <nav className="nav-pills" aria-label="Điều hướng chính">
        {nav.map(({ href, label, icon, badge }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              className={active ? "nav-pill active" : "nav-pill"}
              aria-current={active ? "page" : undefined}
            >
              {/* nền viên đang chọn trượt sang mục mới (CLAUDE.md 9.2: layoutId="active-pill") */}
              {active && <motion.span layoutId="active-pill" className="nav-pill-bg" aria-hidden />}
              <Icon name={icon} size={16} weight={active ? "fill" : "regular"} />
              <span>{label}</span>
              {badge ? (
                <span className="nav-badge" role="status" aria-label={`${badge} cần xử lý`}>
                  {badge}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
      <div className="topbar-tools">
        <RunSearch />
        <RoleChip />
        <Link href="/docs" className="icon-btn" aria-label="Tài liệu dự án" title="Tài liệu dự án">
          <Icon name="docs" size={20} />
        </Link>
        <ThemeToggle />
        <NotificationBell />
        <AvatarMenu />
      </div>
      <GuestStrip />
    </header>
  );
}

/** Nút quay lại: về trang trước trong lịch sử; mở thẳng từ liên kết (không có lịch sử) thì về cấp trên. */
function BackButton() {
  const pathname = usePathname();
  const router = useRouter();
  if (pathname === "/") return null;
  const parent = pathname.startsWith("/runs/") ? "/runs" : "/";
  const goBack = () => (window.history.length > 1 ? router.back() : router.push(parent));
  return (
    <button type="button" className="back-btn" onClick={goBack} aria-label="Quay lại trang trước">
      <Icon name="back" size={16} weight="bold" />
      <span>Quay lại</span>
    </button>
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
  const { auth, user, guest } = useApp();
  // Trang công khai: đăng nhập, /demo (tự bật chế độ khách rồi về trang chủ), /docs (tài liệu dự án)
  const onPublic = ["/login", "/demo", "/docs"].some((path) => pathname.startsWith(path));
  const navItems = useNavItems(user?.role ?? "engineer");

  // Mọi trang (trừ trang công khai) cần phiên; hết phiên → về đăng nhập, quay lại đúng trang sau khi đăng nhập
  useEffect(() => {
    if (auth === "out" && !onPublic) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [auth, onPublic, pathname, router]);

  if (onPublic) return <>{children}</>;
  if (auth !== "in") {
    return (
      <div className="page">
        <Splash text={auth === "checking" ? "Đang kiểm tra phiên đăng nhập…" : "Đang chuyển tới trang đăng nhập…"} />
      </div>
    );
  }
  return (
    <div className="page" data-role={user?.role} data-guest={guest || undefined}>
      <a href="#main" className="skip-link">
        Bỏ qua tới nội dung
      </a>
      <Dock />
      <div className="frame">
        <TopBar />
        <GuideBanner />
        <div className="body">
          <main id="main" className="content">
            <BackButton />
            {children}
          </main>
        </div>
        <Footer />
      </div>
      <BottomNav items={navItems} isActive={(href) => isActive(pathname, href)} />
    </div>
  );
}
