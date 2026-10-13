"use client";

// Mọi icon của giao diện đi qua file này (CLAUDE.md mục 9.11): bộ Phosphor, tên nghiệp vụ ở lib/icons.ts.
// Mặc định: cỡ 16 (trong chữ, bảng), nét `regular`, màu = màu chữ (currentColor), trang trí nên aria-hidden.
// Icon đứng một mình trong nút: truyền `aria-label` (và đặt tooltip ở nút).

import { IconContext, type IconProps, type IconWeight } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

import { ICONS, type IconName } from "@/lib/icons";

export type IconComponentProps = Omit<IconProps, "weight" | "ref" | "name"> & {
  weight?: IconWeight;
  /** Tương thích icon nét cũ: ≥ 3 → nét `bold`. */
  strokeWidth?: number;
};

export function Icon({
  name,
  size = 16,
  weight = "regular",
  strokeWidth,
  ...props
}: IconComponentProps & { name: IconName }) {
  const Glyph = ICONS[name];
  const decorative = !props["aria-label"];
  return (
    <Glyph
      size={size}
      weight={strokeWidth !== undefined && strokeWidth >= 3 ? "bold" : weight}
      aria-hidden={decorative || undefined}
      focusable="false"
      {...props}
    />
  );
}

/**
 * Dấu tích tự vẽ khi một bước xong (CLAUDE.md 9.11: hoạt ảnh pathLength ~250ms). Cùng hình học với `Check` của Phosphor
 * (polyline 40,144 → 96,200 → 224,72 trên khung 256) nhưng vẽ bằng nét để hoạt ảnh được. Giảm chuyển động: hiện ngay.
 */
export function DrawnCheck({ size = 16, weight = "bold" }: { size?: number; weight?: "regular" | "bold" }) {
  const reduce = useReducedMotion();
  return (
    <svg width={size} height={size} viewBox="0 0 256 256" aria-hidden focusable="false">
      <motion.polyline
        points="40 144 96 200 224 72"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={weight === "bold" ? 24 : 16}
        initial={{ pathLength: reduce ? 1 : 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
      />
    </svg>
  );
}

/** Vòng xoay "đang chạy" (CircleNotch) quay đều bằng framer-motion; máy giảm chuyển động thì đứng yên. */
export function SpinningIcon({ size = 16 }: { size?: number }) {
  return (
    <motion.span
      style={{ display: "inline-grid" }}
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 0.9, ease: "linear" }}
    >
      <Icon name="running" size={size} weight="bold" />
    </motion.span>
  );
}

/** Mặc định cho cả app (CLAUDE.md 9.11): nét regular, màu theo chữ. */
export function IconProvider({ children }: { children: ReactNode }) {
  return <IconContext.Provider value={{ weight: "regular", color: "currentColor" }}>{children}</IconContext.Provider>;
}

function named(name: IconName) {
  function NamedIcon(props: IconComponentProps) {
    return <Icon name={name} {...props} />;
  }
  NamedIcon.displayName = `Icon(${name})`;
  return NamedIcon;
}

// Tên cũ giữ nguyên để các màn hình không phải sửa import.
export const BotIcon = named("bot");
export const BellIcon = named("notifications");
export const SparkIcon = named("agent");
export const TerminalIcon = named("terminal");
export const FlowIcon = named("pipeline");
export const ChartIcon = named("chart");
export const CopyIcon = named("copy");
export const CheckIcon = named("check");
export const DatabaseIcon = named("sources");
export const LayersIcon = named("layers");
export const CpuIcon = named("compute");
export const HomeIcon = named("home");
export const ListIcon = named("runs");
export const BookIcon = named("errors");
export const SunIcon = named("light");
export const MoonIcon = named("dark");
export const MonitorIcon = named("system");
export const ArrowUpRightIcon = named("external");
export const PlusIcon = named("add");
export const DocIcon = named("file");
export const ClockIcon = named("pending");
export const PulseIcon = named("monitor");
export const ArrowRightIcon = named("start");
export const ArrowLeftIcon = named("back");
export const UserIcon = named("user");
export const UsersIcon = named("users");
export const LockIcon = named("password");
export const EyeIcon = named("show");
export const EyeOffIcon = named("hide");
export const LogoutIcon = named("logout");

/** Trạng thái: icon `fill` + màu theo `tone` (đặt ở lớp cha) + LUÔN có chữ đi kèm ở nơi dùng. */
export type StatusTone = "ok" | "danger" | "warn" | "info" | "pending" | "running";
const STATUS_ICON: Record<StatusTone, IconName> = {
  ok: "success",
  danger: "failure",
  warn: "warning",
  info: "info",
  pending: "pending",
  running: "running",
};

export function StatusIcon({ tone, size = 16 }: { tone: StatusTone; size?: number }) {
  return (
    <Icon
      name={STATUS_ICON[tone]}
      size={size}
      weight={tone === "pending" ? "duotone" : tone === "running" ? "bold" : "fill"}
      className={tone === "running" ? "icon-spin" : undefined}
    />
  );
}
