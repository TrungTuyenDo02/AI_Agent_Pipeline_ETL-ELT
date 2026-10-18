import type { CSSProperties } from "react";

import type { PipPose } from "@/lib/pip";

const POSITIONS: Record<PipPose, string> = {
  idle: "0% 0%",
  notes: "50% 0%",
  coding: "100% 0%",
  review: "0% 100%",
  error: "50% 100%",
  done: "100% 100%",
};

/** One cached atlas, six poses; decorative unless a label is supplied. */
export function PipSprite({
  pose = "idle",
  size = 96,
  label,
  animated = false,
}: {
  pose?: PipPose;
  size?: number;
  label?: string;
  animated?: boolean;
}) {
  return (
    <span
      className={`pip-sprite${animated ? " pip-sprite-animated" : ""}`}
      data-pose={pose}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      style={{ "--pip-size": `${size}px`, backgroundPosition: POSITIONS[pose] } as CSSProperties}
    />
  );
}
