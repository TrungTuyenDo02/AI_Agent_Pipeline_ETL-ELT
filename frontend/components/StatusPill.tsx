// Nhãn trạng thái: icon Phosphor + màu + chữ (CLAUDE.md 9.11, không dùng ký tự ✓ ✗ làm icon).

import { STATUS_LABELS, STATUS_TONES } from "@/lib/format";
import type { IconName } from "@/lib/icons";
import type { RunStatus } from "@/lib/types";

import { Icon } from "./icons";

const STATUS_ICON: Record<Exclude<RunStatus, "running">, IconName> = {
  waiting_input: "warning",
  waiting_drift: "warning",
  waiting_clarification: "warning",
  waiting_plan_review: "warning",
  waiting_schema: "warning",
  waiting_rescue: "warning",
  waiting_review: "awaitingReview",
  paused: "pause",
  approved: "success",
  failed: "failure",
  rejected_input: "warning",
};

export function StatusPill({ status }: { status: RunStatus }) {
  return (
    <span className={`status-pill ${STATUS_TONES[status]}`}>
      <span className="status-glyph" aria-hidden>
        {status === "running" ? (
          <span className="pulse-dot" />
        ) : (
          <Icon name={STATUS_ICON[status]} size={15} weight="fill" />
        )}
      </span>
      {STATUS_LABELS[status]}
    </span>
  );
}
