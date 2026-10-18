"use client";

// Thanh liên kết neo của /docs, dính đầu trang khi cuộn. Đây là điều hướng trong trang (anchor), không phải bộ tab:
// mọi mục vẫn nằm trên trang, liên kết chỉ cuộn tới đó. Mục đang đọc: aria-current="location".
// - Cuộn tay: tính lại mục đang đọc, KHÔNG đổi URL (không tạo mục lịch sử cho mỗi lần cuộn).
// - Bấm liên kết / mở URL có #, tải lại, Back/Forward: trình duyệt tự cuộn tới neo; ở đây chỉ đánh dấu đúng mục.
// - Chiều cao thật của thanh ghi vào --docs-nav-h để tiêu đề mục không bị thanh che (scroll-padding-top).

import { useEffect, useRef, useState } from "react";

import { Icon } from "../icons";

export interface DocsSection {
  id: string;
  label: string;
}

/** Khoảng (px) dưới thanh dính: tiêu đề mục đi qua vạch này thì mục đó thành "đang đọc". */
const READ_LINE = 32;
const SCROLL_KEYS = new Set(["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "]);

export function DocsSectionNav({ items }: { items: DocsSection[] }) {
  const [active, setActive] = useState(items[0]?.id ?? "");
  const [open, setOpen] = useState(false);
  const bar = useRef<HTMLElement>(null);

  useEffect(() => {
    const root = document.documentElement;
    const nav = bar.current;
    if (!nav) return;
    const ids = items.map((item) => item.id);

    const setOffset = () => root.style.setProperty("--docs-nav-h", `${Math.ceil(nav.offsetHeight)}px`);
    setOffset();
    const resize = new ResizeObserver(setOffset);
    resize.observe(nav);

    // Sau khi bấm liên kết (hoặc mở #), giữ mục đã chọn tới khi người dùng tự cuộn tiếp: mục cuối ngắn không cuộn
    // tới đỉnh được, nếu không giữ thì vạch đọc sẽ chọn nhầm mục khác.
    let target: string | null = null;
    let pinnedAt: number | null = null;
    let settleTimer = 0;
    let frame = 0;

    const compute = () => {
      frame = 0;
      if (target) return;
      if (pinnedAt !== null) {
        if (Math.abs(window.scrollY - pinnedAt) < 4) return;
        pinnedAt = null;
      }
      const line = nav.getBoundingClientRect().bottom + READ_LINE;
      const atBottom = window.innerHeight + window.scrollY >= root.scrollHeight - 2;
      let current = ids[0];
      if (atBottom) current = ids[ids.length - 1];
      else
        for (const id of ids) {
          const section = document.getElementById(id);
          if (section && section.getBoundingClientRect().top <= line) current = id;
        }
      setActive(current);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(compute);
    };
    // Cuộn do bấm liên kết kết thúc khi 150 ms không có sự kiện cuộn nào
    const settle = () => {
      window.clearTimeout(settleTimer);
      settleTimer = window.setTimeout(() => {
        target = null;
        pinnedAt = window.scrollY;
      }, 150);
    };
    const onScroll = () => (target ? settle() : schedule());
    // Người dùng tự cuộn (bánh xe, chạm, kéo thanh cuộn, phím cuộn), kể cả giữa lúc trang đang cuộn mượt tới neo:
    // bỏ khóa ngay để mục đang đọc theo vị trí thật.
    const release = () => {
      if (!target && pinnedAt === null) return;
      window.clearTimeout(settleTimer);
      target = null;
      pinnedAt = null;
      schedule();
    };
    const onKey = (event: KeyboardEvent) => {
      if (SCROLL_KEYS.has(event.key)) release();
    };
    const userInput = ["wheel", "touchstart", "pointerdown"] as const;
    const followHash = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!ids.includes(id)) {
        target = null;
        pinnedAt = null;
        schedule();
        return;
      }
      target = id;
      setActive(id);
      settle();
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", schedule);
    window.addEventListener("hashchange", followHash);
    userInput.forEach((type) => window.addEventListener(type, release, { passive: true }));
    window.addEventListener("keydown", onKey);
    if (window.location.hash) followHash();
    else compute();
    return () => {
      resize.disconnect();
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", schedule);
      window.removeEventListener("hashchange", followHash);
      userInput.forEach((type) => window.removeEventListener(type, release));
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(settleTimer);
      if (frame) cancelAnimationFrame(frame);
      root.style.removeProperty("--docs-nav-h");
    };
  }, [items]);

  // Danh sách trên điện thoại: đóng khi bấm ra ngoài hoặc nhấn Esc
  const menu = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !menu.current?.contains(event.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const current = items.find((item) => item.id === active) ?? items[0];
  const links = (
    <ol className="docs-sectionnav-list" id="docs-sections">
      {items.map((item) => (
        <li key={item.id}>
          <a
            href={`#${item.id}`}
            aria-current={item.id === active ? "location" : undefined}
            // Bấm lại đúng mục đang ở (# không đổi → không có hashchange): vẫn đánh dấu ngay
            onClick={() => {
              setActive(item.id);
              setOpen(false);
            }}
          >
            {item.label}
          </a>
        </li>
      ))}
    </ol>
  );

  return (
    <nav className="docs-sectionnav" aria-label="Các phần của trang" ref={bar}>
      <div className="docs-sectionnav-inner" ref={menu}>
        <button
          type="button"
          className="docs-sectionnav-toggle"
          aria-expanded={open}
          aria-controls="docs-sections"
          onClick={() => setOpen(!open)}
        >
          <span>
            Đang xem: <strong>{current?.label}</strong>
          </span>
          <Icon name="caret" size={16} weight="bold" />
        </button>
        <div className={open ? "docs-sectionnav-links open" : "docs-sectionnav-links"}>{links}</div>
      </div>
    </nav>
  );
}
