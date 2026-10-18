"use client";

// Phần tương tác của trang /docs (trang còn lại là Server Component để có tiêu đề, mô tả trang).

import { useEffect } from "react";

import { useApp } from "../AppContext";
import { Icon } from "../icons";

/**
 * Hiện dần các khối có `data-reveal` khi cuộn tới. Không có JS hoặc máy bật "giảm chuyển động" thì mọi khối hiện
 * ngay: CSS chỉ ẩn khối khi <html data-reveal="on">, và cờ này chỉ được đặt ở đây.
 */
export function DocsReveal() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
    const root = document.documentElement;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    document.querySelectorAll(".docs-page [data-reveal]").forEach((element) => observer.observe(element));
    root.dataset.reveal = "on";
    return () => {
      observer.disconnect();
      delete root.dataset.reveal;
    };
  }, []);
  return null;
}

export function DocsThemeToggle() {
  const { dark, setTheme } = useApp();
  const label = dark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối";
  return (
    <button
      type="button"
      className="docs-icon-btn"
      aria-label={label}
      title={label}
      onClick={() => setTheme(dark ? "light" : "dark")}
    >
      <Icon name={dark ? "light" : "dark"} size={20} weight="fill" />
    </button>
  );
}
