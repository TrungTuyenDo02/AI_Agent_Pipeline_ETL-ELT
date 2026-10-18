// Bộ máy của chế độ khách: trạng thái các lần chạy mẫu (sessionStorage) + dựng RunDetail từ ảnh chụp thật (mock).
// Tiến trình "đang chạy" tính theo đồng hồ: mỗi lần hỏi, lần chạy đi tiếp các khung đã đủ thời gian — không cần hẹn giờ.

import { DEMO_STATE_KEY, GUEST_USERS, readSession, writeSession } from "../guest";
import type { CatalogView, RunDetail, RunFiles, RunRecord, RunStatus, StepEvent } from "../types";

import { FIXTURES, RUN_TOKEN } from "./fixtures";
import type { DemoFrame, DemoPhase } from "./types";

/** Giai đoạn chạy (có khung tiến trình) → điểm dừng chờ người ở cuối giai đoạn. */
const RUNNING_TO_WAITING = {
  intake: "clarify",
  plan: "plan_review",
  build: "review",
  approve: "approved",
} as const satisfies Record<DemoPhase, string>;
type Waiting = (typeof RUNNING_TO_WAITING)[DemoPhase];
export type RunPhase = DemoPhase | Waiting | "failed";

const SNAPSHOT_OF: Record<Waiting, keyof typeof FIXTURES.snapshots> = {
  clarify: "clarify",
  plan_review: "plan",
  review: "review",
  approved: "approved",
};
const PHASE_ORDER: DemoPhase[] = ["intake", "plan", "build", "approve"];

export interface DemoRun {
  id: string;
  kind: "main" | "stopped";
  request: string;
  requester: string;
  createdAt: number; // ms
  phase: RunPhase;
  phaseAt: number; // ms: lúc vào giai đoạn hiện tại
  /** ms: lúc bắt đầu (lần gần nhất) mỗi giai đoạn chạy — để tính giờ xong của từng bước */
  starts: Partial<Record<DemoPhase, number>>;
  answers?: Record<string, string | string[]>;
  reviewRounds: number;
  updatedAt: number;
  /** Biến thể của ảnh chụp chờ duyệt: `skipped` = không có bản sửa, `legacy` = checkpoint cũ (chưa có số đo mới). */
  variant?: "skipped" | "legacy";
}

export interface DemoState {
  v: 2;
  seq: number;
  runs: DemoRun[];
  /** Sổ lỗi: mục Reviewer đã duyệt/bỏ trong phiên khách */
  errorDecisions: Record<string, "approve" | "reject">;
}

const MINUTE = 60_000;
const DAY = 24 * 60 * MINUTE;

function phaseDuration(phase: DemoPhase): number {
  return FIXTURES.phases[phase].reduce((total, frame) => total + frame.dur * 1000, 0);
}

/** Lần chạy đã đi trọn các giai đoạn tới `until` (giai đoạn đó cũng xong), bắt đầu từ `start`. */
function finishedRun(
  base: Omit<DemoRun, "phase" | "phaseAt" | "starts" | "updatedAt">,
  until: DemoPhase,
  gapMs: number,
) {
  const starts: Partial<Record<DemoPhase, number>> = {};
  let at = base.createdAt;
  for (const phase of PHASE_ORDER) {
    starts[phase] = at;
    at += phaseDuration(phase);
    if (phase === until) break;
    at += gapMs; // người dùng trả lời/duyệt sau một lúc
  }
  return { ...base, phase: RUNNING_TO_WAITING[until], phaseAt: at, starts, updatedAt: at };
}

/** Bộ mẫu ban đầu: hoàn tất (có tối ưu được áp dụng), chờ duyệt, đã dừng, đang chạy. */
export function initialState(now: number): DemoState {
  const owner = GUEST_USERS.engineer.name;
  const approved = finishedRun(
    {
      id: "mau-hoan-tat",
      kind: "main",
      request: FIXTURES.request,
      requester: owner,
      createdAt: now - 2 * DAY,
      reviewRounds: 0,
    },
    "approve",
    3 * MINUTE,
  );
  const waiting = finishedRun(
    {
      id: "mau-cho-duyet",
      kind: "main",
      request: "Báo cáo doanh thu ngày gộp từ Sàn A, Sàn B và website, chỉ tính đơn hoàn tất",
      requester: owner,
      createdAt: now - 50 * MINUTE,
      reviewRounds: 0,
    },
    "build",
    2 * MINUTE,
  );
  const stopped: DemoRun = {
    id: "mau-da-dung",
    kind: "stopped",
    request: FIXTURES.stoppedRequest,
    requester: owner,
    createdAt: now - DAY,
    phase: "failed",
    phaseAt: now - DAY + 5 * MINUTE,
    starts: {},
    reviewRounds: 0,
    updatedAt: now - DAY + 5 * MINUTE,
  };
  // Đang chạy: đã qua hỏi làm rõ và duyệt kế hoạch, đang sinh code + chạy thử (tiến trình chạy theo đồng hồ)
  const runningStart = now - 3 * MINUTE;
  const running: DemoRun = {
    id: "mau-dang-chay",
    kind: "main",
    request: "Doanh thu theo ngày của 3 kênh bán, chạy lại mỗi sáng",
    requester: owner,
    createdAt: runningStart,
    phase: "build",
    phaseAt: now,
    starts: { intake: runningStart, plan: runningStart + MINUTE, build: now },
    reviewRounds: 0,
    updatedAt: now,
  };
  const variants = (["skipped", "legacy"] as const).map((variant, i) =>
    finishedRun(
      {
        id: variant === "skipped" ? "mau-giu-nguyen" : "mau-checkpoint-cu",
        kind: "main",
        request:
          variant === "skipped"
            ? "Doanh thu ngày 3 kênh (mẫu: optimizer giữ nguyên bản gốc)"
            : "Doanh thu ngày 3 kênh (mẫu: lần chạy cũ, chưa có số đo từng model)",
        requester: owner,
        createdAt: now - (70 + 20 * i) * MINUTE,
        reviewRounds: 0,
        variant,
      },
      "build",
      2 * MINUTE,
    ),
  );
  return { v: 2, seq: 0, runs: [running, waiting, ...variants, stopped, approved], errorDecisions: {} };
}

export function loadState(now = Date.now()): DemoState {
  const raw = readSession(DEMO_STATE_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as DemoState;
      if (parsed.v === 2 && Array.isArray(parsed.runs)) return parsed;
    } catch {
      // hỏng: dựng lại bộ mẫu
    }
  }
  const state = initialState(now);
  saveState(state);
  return state;
}

export function saveState(state: DemoState): void {
  writeSession(DEMO_STATE_KEY, JSON.stringify(state));
}

function isRunning(phase: RunPhase): phase is DemoPhase {
  return (PHASE_ORDER as string[]).includes(phase);
}

/** Đi tiếp các giai đoạn chạy đã đủ thời gian. Trả true nếu có đổi (cần lưu). */
export function advance(run: DemoRun, now: number): boolean {
  if (!isRunning(run.phase)) return false;
  const end = run.phaseAt + phaseDuration(run.phase);
  if (now < end) return false;
  run.phase = RUNNING_TO_WAITING[run.phase];
  run.phaseAt = end;
  run.updatedAt = end;
  return true;
}

/** Bắt đầu một giai đoạn chạy (sau khi người dùng gửi thao tác). */
export function startPhase(run: DemoRun, phase: DemoPhase, now: number): void {
  run.phase = phase;
  run.phaseAt = now;
  run.starts[phase] = now;
  run.updatedAt = now;
}

export function isBusy(run: DemoRun): boolean {
  return isRunning(run.phase);
}

/** Khung đang hiện của giai đoạn chạy + mốc bắt đầu khung (ms). */
function currentFrame(run: DemoRun & { phase: DemoPhase }, now: number): { frame: DemoFrame; startedAt: number } {
  const frames = FIXTURES.phases[run.phase];
  let at = run.phaseAt;
  for (const frame of frames) {
    if (now < at + frame.dur * 1000) return { frame, startedAt: at };
    at += frame.dur * 1000;
  }
  const last = frames[frames.length - 1];
  return { frame: last, startedAt: at - last.dur * 1000 };
}

/** Giai đoạn chứa bước thứ `index` (theo số bước có ở ảnh chụp cuối mỗi giai đoạn). */
function phaseOfEvent(index: number): DemoPhase {
  const { clarify, plan, review } = FIXTURES.snapshots;
  if (index < clarify.events.length) return "intake";
  if (index < plan.events.length) return "plan";
  return index < review.events.length ? "build" : "approve";
}

/** Giờ xong (epoch giây) của bước thứ `index`: theo dòng thời gian giả lập của giai đoạn chứa nó. */
function eventTime(run: DemoRun, index: number): number {
  const phase = phaseOfEvent(index);
  let at = run.starts[phase] ?? run.createdAt;
  for (const frame of FIXTURES.phases[phase]) {
    if (frame.events_count > index) return at / 1000;
    at += frame.dur * 1000;
  }
  return at / 1000;
}

function withRunId<T>(value: T, id: string): T {
  return JSON.parse(JSON.stringify(value).split(RUN_TOKEN).join(id)) as T;
}

function iso(ms: number): string {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "+00:00");
}

/** Chi tiết lần chạy như GET /runs/{id} trả về. */
/** Ca demo "giữ nguyên" và "checkpoint cũ" dựng từ ảnh chụp chờ duyệt thật (ca "có bản sửa"). */
function applyVariant(detail: RunDetail, variant: DemoRun["variant"]): RunDetail {
  const opt = detail.optimization;
  if (variant === "skipped") {
    const reason = "Mẫu: không có bản viết lại nào nhanh hơn ngưỡng và giữ đúng kết quả; giữ nguyên bản gốc.";
    const gate = detail.review_gate;
    const kept = "Không áp dụng bản tối ưu: giữ nguyên bản gốc.";
    return {
      ...detail,
      optimization: { ...opt, decision: "skipped", proposed_sql: "", after: null, improvement_pct: null, reason },
      review_gate: gate && {
        ...gate,
        extra: gate.extra.map((c) => (c.id === "optimization" ? { ...c, status: "passed", reason: kept } : c)),
      },
    };
  }
  if (variant === "legacy") {
    const sandbox = { ...detail.sandbox };
    delete sandbox.model_timings;
    delete sandbox.wall_ms;
    delete sandbox.dbt_invocation;
    const rest = { ...opt };
    delete rest.bottlenecks;
    const strip = (m: typeof opt.before) => (m ? { median_ms: m.median_ms, runs: m.runs } : m);
    const measured = (detail.evidence.measured ?? []).filter((m) => !["Đo hiệu năng", "Điểm nghẽn"].includes(m.node));
    return {
      ...detail,
      sandbox,
      optimization: { ...rest, before: strip(opt.before), after: strip(opt.after) },
      evidence: { ...detail.evidence, measured },
    };
  }
  return detail;
}

export function buildDetail(run: DemoRun, now: number): RunDetail {
  let detail: RunDetail;
  let eventCount: number;
  if (run.kind === "stopped") {
    detail = withRunId(FIXTURES.stopped.detail, run.id);
    detail.events = detail.events.map((event, i) => ({
      ...event,
      finished_at: run.createdAt / 1000 + (FIXTURES.stopped.eventOffsets[i] ?? 0),
    }));
    eventCount = detail.events.length;
  } else if (isRunning(run.phase)) {
    const running = run as DemoRun & { phase: DemoPhase };
    const { frame, startedAt } = currentFrame(running, now);
    const base = FIXTURES.snapshots[SNAPSHOT_OF[RUNNING_TO_WAITING[running.phase]]];
    detail = withRunId({ ...base, ...frame.patch } as RunDetail, run.id);
    if (detail.current) {
      detail.current = { ...detail.current, started_at: startedAt / 1000, elapsed_s: (now - startedAt) / 1000 };
    }
    eventCount = frame.events_count;
  } else {
    detail = applyVariant(withRunId(FIXTURES.snapshots[SNAPSHOT_OF[run.phase as Waiting]], run.id), run.variant);
    eventCount = detail.events.length;
  }
  if (run.kind === "main") {
    const all: StepEvent[] = FIXTURES.snapshots.approved.events;
    detail.events = all.slice(0, eventCount).map((event, i) => ({ ...event, finished_at: eventTime(run, i) }));
  }
  if (run.answers && detail.answered.length) {
    const answers = run.answers;
    detail.answered = detail.answered.map((a) => {
      const value = answers[a.id];
      return value === undefined ? a : { ...a, answer: Array.isArray(value) ? value.join(", ") : value };
    });
  }
  detail.record = {
    ...detail.record,
    id: run.id,
    request_text: run.request,
    requester: run.requester,
    created_at: iso(run.createdAt),
    updated_at: iso(isRunning(run.phase) ? now : run.updatedAt),
    summary: { ...detail.record.summary, review_rounds: run.reviewRounds },
  };
  return detail;
}

export function recordOf(run: DemoRun, now: number): RunRecord {
  return buildDetail(run, now).record;
}

export function statusOf(run: DemoRun, now: number): RunStatus {
  return recordOf(run, now).status;
}

/** Đã có code (chờ duyệt / duyệt / đã duyệt) thì có file và cấu trúc dữ liệu. */
function hasCode(run: DemoRun): boolean {
  return run.kind === "main" && ["review", "approve", "approved"].includes(run.phase);
}

const NO_FILES: RunFiles = { code_files: {}, test_files: {}, previous_files: {} };

export function filesOf(run: DemoRun): RunFiles {
  if (run.kind === "stopped") return withRunId(FIXTURES.stopped.files, run.id);
  return hasCode(run) ? withRunId(FIXTURES.files, run.id) : NO_FILES;
}

export function catalogOf(run: DemoRun): CatalogView {
  return hasCode(run) ? FIXTURES.catalog : { tables: [], lineage: [], joins: [] };
}
