"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { API_URL } from "@/lib/api";

import { useApp } from "./AppContext";
import { Topbar } from "./Topbar";

const NAV = [
  { href: "/", label: "Lần chạy", hint: "Tạo yêu cầu, theo dõi, duyệt" },
  { href: "/catalog", label: "Dữ liệu nguồn", hint: "Bảng, schema, khóa nối" },
  { href: "/errors", label: "Sổ lỗi", hint: "Duyệt bài học cho agent" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/runs");
  return pathname.startsWith(href);
}

function Sidebar() {
  const pathname = usePathname();
  const { status } = useApp();
  return (
    <aside className="sidebar">
      <Link href="/" className="brand">
        <span className="brand-mark" aria-hidden>
          P
        </span>
        <span>
          <strong>P-113</strong>
          <small>Pipeline Agent</small>
        </span>
      </Link>
      <nav aria-label="Điều hướng chính">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={isActive(pathname, item.href) ? "nav-item active" : "nav-item"}
            aria-current={isActive(pathname, item.href) ? "page" : undefined}
          >
            <span>{item.label}</span>
            <small>{item.hint}</small>
          </Link>
        ))}
      </nav>
      <div className="sidebar-foot">
        <small>{status?.agent ?? "P-113 Pipeline Agent"}</small>
        <small className="mono" suppressHydrationWarning>
          API: {API_URL}
        </small>
      </div>
    </aside>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Bỏ qua tới nội dung
      </a>
      <Sidebar />
      <div className="workspace">
        <Topbar />
        <main id="main" className="content">
          {children}
        </main>
      </div>
    </div>
  );
}
