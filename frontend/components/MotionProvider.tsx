"use client";

import { MotionConfig } from "framer-motion";
import type { ReactNode } from "react";

/** Lò xo chuẩn của giao diện (CLAUDE.md 9.3). */
export const SPRING = { type: "spring", stiffness: 400, damping: 28 } as const;

/** reducedMotion="user": máy bật "giảm chuyển động" thì framer-motion bỏ dịch chuyển/phóng to, chỉ giữ mờ dần (9.9). */
export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user" transition={SPRING}>
      {children}
    </MotionConfig>
  );
}
