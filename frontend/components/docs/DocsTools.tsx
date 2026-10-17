"use client";

// Phần tương tác của trang /docs (trang còn lại là Server Component để có tiêu đề, mô tả trang).

import { useApp } from "../AppContext";
import { Icon } from "../icons";

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
