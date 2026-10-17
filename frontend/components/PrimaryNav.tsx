"use client";

// Điều hướng chính theo vai trò: hàng thứ hai của thanh trên (laptop) và thanh dưới đáy (điện thoại < 640px).
// Laptop: đo bề rộng thật của từng mục (đổi theo cỡ chữ, phóng to trình duyệt); mục không vừa chuyển vào menu "Thêm"
// thay vì cuộn ngang, cắt nhãn hay thu nhỏ chữ.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

import type { IconName } from "@/lib/icons";

import { Icon } from "./icons";
import { useDismiss } from "./NotificationBell";

export interface NavLinkItem {
  href: string;
  label: string;
  icon: IconName;
  /** Số đỏ cạnh nhãn (ví dụ số thay đổi cấu trúc chặn đang mở); 0 hoặc trống = không hiện. */
  badge?: number;
}

type IsActive = (href: string) => boolean;

function Badge({ count }: { count?: number }) {
  if (!count) return null;
  return (
    <span className="nav-badge" role="status" aria-label={`${count} cần xử lý`}>
      {count}
    </span>
  );
}

/** Menu "Thêm": các mục không đủ chỗ. Đóng khi bấm ra ngoài, Esc hoặc khi đã chuyển trang. */
function MoreMenu({
  items,
  isActive,
  className,
  up = false,
}: {
  items: NavLinkItem[];
  isActive: IsActive;
  className: string;
  up?: boolean;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const box = useDismiss(open, () => setOpen(false));
  const [shownFor, setShownFor] = useState(pathname);
  if (shownFor !== pathname) {
    setShownFor(pathname);
    setOpen(false);
  }
  const current = items.find((item) => isActive(item.href));
  const badges = items.reduce((sum, item) => sum + (item.badge ?? 0), 0);
  return (
    <div className="popover nav-more" ref={box}>
      <button
        type="button"
        className={current ? `${className} active` : className}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <Icon name="menu" size={18} weight="bold" />
        <span>Thêm</span>
        {current && <span className="sr-only">(đang ở: {current.label})</span>}
        <Badge count={badges} />
      </button>
      {open && (
        <div
          className={up ? "flyout menu nav-more-menu up" : "flyout menu nav-more-menu"}
          role="dialog"
          aria-label="Mục khác"
        >
          <ul>
            {items.map(({ href, label, icon, badge }) => {
              const active = isActive(href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={active ? "nav-more-link active" : "nav-more-link"}
                    aria-current={active ? "page" : undefined}
                    onClick={() => setOpen(false)}
                  >
                    <Icon name={icon} size={18} weight={active ? "fill" : "regular"} />
                    <span>{label}</span>
                    <Badge count={badge} />
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function NavLink({ item, active }: { item: NavLinkItem; active: boolean }) {
  return (
    <Link
      href={item.href}
      className={active ? "nav-link active" : "nav-link"}
      aria-current={active ? "page" : undefined}
    >
      <Icon name={item.icon} size={18} weight={active ? "fill" : "regular"} />
      <span>{item.label}</span>
      <Badge count={item.badge} />
    </Link>
  );
}

// useLayoutEffect chỉ chạy ở trình duyệt; khi dựng trên máy chủ dùng useEffect để tránh cảnh báo.
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

/** Hàng điều hướng chính trên laptop/máy tính bảng: hiện số mục vừa khung, phần còn lại vào "Thêm". */
export function PrimaryNav({ items, isActive }: { items: NavLinkItem[]; isActive: IsActive }) {
  const box = useRef<HTMLDivElement>(null);
  const ruler = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState(items.length);
  const signature = items.map((item) => `${item.href}:${item.label}:${item.badge ?? 0}`).join("|");

  useIsoLayoutEffect(() => {
    const wrap = box.current;
    const measure = ruler.current;
    if (!wrap || !measure) return;
    const compute = () => {
      // Thước đo vẽ sẵn mọi mục ở chữ đậm (trạng thái rộng nhất) + nút "Thêm" ở cuối
      const widths = Array.from(measure.children, (child) => child.getBoundingClientRect().width);
      const more = widths.pop() ?? 0;
      const gap = parseFloat(getComputedStyle(measure).columnGap) || 0;
      const room = wrap.clientWidth;
      const all = widths.reduce((sum, width) => sum + width, 0) + gap * Math.max(0, widths.length - 1);
      if (all <= room) return setFit(widths.length);
      let used = more;
      let count = 0;
      for (const width of widths) {
        if (used + gap + width > room) break;
        used += gap + width;
        count += 1;
      }
      setFit(Math.max(1, count));
    };
    compute();
    const observer = new ResizeObserver(compute);
    observer.observe(wrap);
    observer.observe(measure);
    return () => observer.disconnect();
  }, [signature]);

  const shown = items.slice(0, fit);
  const hidden = items.slice(fit);
  return (
    <nav className="primary-nav" aria-label="Điều hướng chính" ref={box}>
      <ul className="nav-list">
        {shown.map((item) => (
          <li key={item.href}>
            <NavLink item={item} active={isActive(item.href)} />
          </li>
        ))}
        {hidden.length > 0 && (
          <li>
            <MoreMenu items={hidden} isActive={isActive} className="nav-link" />
          </li>
        )}
      </ul>
      {/* Thước đo ẩn: không đọc được, không bấm được, không làm trang rộng ra */}
      <div className="nav-ruler-box" aria-hidden="true">
        <div className="nav-list nav-ruler" ref={ruler}>
          {items.map((item) => (
            <span key={item.href} className="nav-link active">
              <Icon name={item.icon} size={18} />
              <span>{item.label}</span>
              <Badge count={item.badge} />
            </span>
          ))}
          <span className="nav-link">
            <Icon name="menu" size={18} />
            <span>Thêm</span>
          </span>
        </div>
      </div>
    </nav>
  );
}

const CREATE: NavLinkItem = { href: "/#request", label: "Tạo mới", icon: "create" };

/**
 * Thanh dưới đáy (< 640px): tối đa 5 ô để nhãn không bị cắt. Engineer có ô "Tạo mới" ở giữa.
 * Mục còn lại vào "Thêm" (mở lên trên). Chỉ một mục dư thì hiện thẳng mục đó.
 */
export function BottomNav({
  items,
  isActive,
  canCreate,
}: {
  items: NavLinkItem[];
  isActive: IsActive;
  canCreate: boolean;
}) {
  const slots = canCreate ? 3 : 4;
  const direct = items.length <= slots + 1 ? items : items.slice(0, slots);
  const rest = items.slice(direct.length);
  const cells: (NavLinkItem | "create")[] = [...direct];
  if (canCreate) cells.splice(Math.min(2, cells.length), 0, "create");
  return (
    <nav className="bottom-nav" aria-label="Điều hướng chính (điện thoại)">
      {cells.map((cell) => {
        if (cell === "create")
          return (
            <Link key="create" href={CREATE.href} className="bottom-item create">
              <Icon name={CREATE.icon} size={26} />
              <span>{CREATE.label}</span>
            </Link>
          );
        const active = isActive(cell.href);
        return (
          <Link
            key={cell.href}
            href={cell.href}
            className={active ? "bottom-item active" : "bottom-item"}
            aria-current={active ? "page" : undefined}
          >
            <Icon name={cell.icon} size={22} weight={active ? "fill" : "regular"} />
            <span>{cell.label}</span>
            <Badge count={cell.badge} />
          </Link>
        );
      })}
      {rest.length > 0 && <MoreMenu items={rest} isActive={isActive} className="bottom-item" up />}
    </nav>
  );
}
