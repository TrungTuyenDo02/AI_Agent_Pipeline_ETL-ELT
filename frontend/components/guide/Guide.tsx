"use client";

// Hướng dẫn nhúng sẵn trong trang, CHỈ hiện ở chế độ khách (không có tour lớp phủ). Ngoài chế độ khách mọi khối
// ở đây trả về null nên giao diện y hệt cũ. Chữ nằm ở lib/guideText.ts; trạng thái lấy từ dữ liệu thật của lần chạy.

import Link from "next/link";

import { GUEST_RUN_PREFIX } from "@/lib/guest";
import {
  GUIDE_BANNER,
  GUIDE_DONE,
  GUIDE_GLOSSARY,
  GUIDE_NOTES,
  GUIDE_STEP_STATE,
  GUIDE_STEPS,
  STATUS_EXPLAIN,
  type GuideStepId,
} from "@/lib/guideText";
import type { RunDetail, RunRecord, RunStatus, Stage } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

import { useApp } from "../AppContext";
import { DrawnCheck, Icon, SpinningIcon } from "../icons";
import { PHASES } from "../run/PipelineTrack";
import { useRun } from "../run/RunContext";

type StepState = keyof typeof GUIDE_STEP_STATE | "start";

/** Thoát chế độ khách và về đăng nhập (dùng chung cho các nút "Đăng nhập để chạy thật"). */
function LoginButton({ label, primary = true }: { label: string; primary?: boolean }) {
  const { exitGuest } = useApp();
  return (
    <button
      type="button"
      className={primary ? "btn guide-btn primary" : "btn guide-btn"}
      onClick={() => exitGuest("/login")}
    >
      {label}
    </button>
  );
}

/** 1. Dải thông báo ngay dưới thanh trên. */
export function GuideBanner() {
  const { guest } = useApp();
  if (!guest) return null;
  return (
    <section className="guide-banner" aria-labelledby="guide-banner-title">
      <Icon name="info" size={22} weight="duotone" className="guide-banner-icon" />
      <div className="guide-banner-text">
        <h2 id="guide-banner-title">{GUIDE_BANNER.title}</h2>
        <p>{GUIDE_BANNER.text}</p>
      </div>
      <div className="guide-actions">
        <LoginButton label={GUIDE_BANNER.login} />
        <LoginButton label={GUIDE_BANNER.exit} primary={false} />
      </div>
    </section>
  );
}

const OTHER_PHASE_STAGES = new Set(PHASES.filter((p) => p.id !== "understand").flatMap((p) => p.stages));

/** Bước con thuộc một bước lớn. Bước 1 gồm cả các cửa kiểm tra đầu vào (không nằm trong 3 giai đoạn sau). */
function stagesOf(phaseId: string, stages: Stage[]): Stage[] {
  if (phaseId === "understand") return stages.filter((s) => !OTHER_PHASE_STAGES.has(s.id));
  const ids = PHASES.find((p) => p.id === phaseId)?.stages ?? [];
  return stages.filter((s) => ids.includes(s.id));
}

const STOPPED: RunStatus[] = ["failed", "rejected_input"];

/**
 * Trạng thái một bước lớn theo lời thường. Khác thanh tiến trình kỹ thuật: bước con "lỗi" khi lần chạy CHƯA dừng là
 * agent đang tự xử lý (ví dụ soát đặc tả chưa đạt nên hỏi lại, sandbox lỗi nên tự sửa) — không gọi là "đã dừng".
 */
function stepState(stages: Stage[], stopped: boolean): StepState {
  if (stages.some((s) => s.state === "human")) return "human";
  if (stages.some((s) => s.state === "failed")) return stopped ? "failed" : "running";
  if (stages.some((s) => s.state === "running")) return "running";
  return stages.length > 0 && stages.every((s) => s.state === "passed") ? "done" : "waiting";
}

/** Trạng thái 4 bước lớn suy từ trạng thái thật của các bước con (máy chủ / dữ liệu mẫu trả về). */
export function stepStates(detail: RunDetail | null): StepState[] {
  if (!detail) return ["start", "waiting", "waiting", "waiting"];
  const stages = detail.stages ?? [];
  const { status } = detail.record;
  return GUIDE_STEPS.map((step) =>
    status === "approved" ? "done" : stepState(stagesOf(step.phase, stages), STOPPED.includes(status)),
  );
}

function StepMark({ state, index }: { state: StepState; index: number }) {
  if (state === "done") return <DrawnCheck size={16} />;
  if (state === "running") return <SpinningIcon size={16} />;
  if (state === "failed") return <Icon name="close" size={16} weight="bold" />;
  if (state === "human") return <Icon name="awaitingReview" size={16} weight="bold" />;
  return <span aria-hidden>{index + 1}</span>;
}

const START_TEXT = "Bắt đầu ở đây";

/** 2. Khối "Quy trình 4 bước": bước hiện tại tô đậm, bước xong có dấu tích; trạng thái luôn có chữ đi kèm. */
export function GuideSteps({ detail, caption }: { detail: RunDetail | null; caption?: React.ReactNode }) {
  const states = stepStates(detail);
  const current = states.findIndex((s) => s !== "done");
  return (
    <section className="guide-steps" aria-labelledby="guide-steps-title">
      <header className="guide-steps-head">
        <h2 id="guide-steps-title">Quy trình 4 bước</h2>
        {caption && <p className="guide-steps-caption">{caption}</p>}
      </header>
      <ol className="guide-step-list">
        {GUIDE_STEPS.map((step, index) => {
          const state = states[index];
          const isCurrent = index === current;
          return (
            <li
              key={step.id}
              className="guide-step"
              data-state={state}
              data-current={isCurrent || undefined}
              aria-current={isCurrent ? "step" : undefined}
            >
              <span className="guide-step-mark">
                <StepMark state={state} index={index} />
              </span>
              <span className="guide-step-body">
                <strong>
                  {index + 1}. {step.title}
                </strong>
                <span className="guide-step-state">{state === "start" ? START_TEXT : GUIDE_STEP_STATE[state]}</span>
                <span className="guide-step-text">{step.text}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/** Lần chạy mới nhất (theo giờ tạo) để khối 4 bước ở trang chủ đi theo trạng thái thật của nó. */
function latestRun(runs: RunRecord[] | null): RunRecord | null {
  return [...(runs ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null;
}

/** Khối 4 bước ở trang chủ: theo lần chạy gần nhất; chưa có lần chạy nào thì chỉ vào bước 1. */
export function HomeGuideSteps() {
  const { guest, runs } = useApp();
  const latest = guest ? latestRun(runs) : null;
  const polled = usePoll<RunDetail>(latest ? `/runs/${latest.id}` : null, 3000);
  if (!guest) return null;
  const detail = polled.data && latest && polled.data.record.id === latest.id ? polled.data : null;
  return (
    <div className="dash-wide">
      <GuideSteps
        detail={detail}
        caption={
          latest ? (
            <>
              Theo lần chạy gần nhất: <Link href={`/runs/${latest.id}`}>{latest.request_text}</Link>
            </>
          ) : (
            "Bắt đầu bằng khung Yêu cầu mới."
          )
        }
      />
    </div>
  );
}

/** Khối 4 bước ở trang chi tiết lần chạy. */
export function RunGuideSteps() {
  const { guest } = useApp();
  const { detail } = useRun();
  if (!guest || !detail) return null;
  return <GuideSteps detail={detail} />;
}

/** 4. Khung giải thích ngắn của một giai đoạn. */
export function GuideNote({ id }: { id: keyof typeof GUIDE_NOTES }) {
  const { guest } = useApp();
  if (!guest) return null;
  const note = GUIDE_NOTES[id];
  return (
    <aside className="guide-note" aria-label={note.title}>
      <Icon name="info" size={20} weight="duotone" className="guide-note-icon" />
      <div>
        <strong>{note.title}</strong>
        <p>{note.text}</p>
      </div>
    </aside>
  );
}

/** Màn duyệt: giải thích diff/duyệt (giả lập) và code AI viết, đặt cạnh nhau. */
export function ReviewGuide() {
  const { guest } = useApp();
  if (!guest) return null;
  return (
    <div className="guide-note-row">
      <GuideNote id="review" />
      <GuideNote id="code" />
    </div>
  );
}

/** Màn tổng quan: giải thích giai đoạn lần chạy đang ở (hoặc dừng lại). */
export function StageGuide() {
  const { detail } = useRun();
  if (!detail) return null;
  const states = stepStates(detail);
  const index = states.findIndex((s) => s !== "done");
  const id: GuideStepId = GUIDE_STEPS[index === -1 ? GUIDE_STEPS.length - 1 : index].id;
  return <GuideNote id={id} />;
}

/** 5. Dòng giải thích theo trạng thái thật của lần chạy. */
export function StatusExplain({ status }: { status: RunStatus }) {
  const { guest } = useApp();
  if (!guest) return null;
  return (
    <p className="guide-status-line">
      <Icon name="info" size={16} weight="bold" /> {STATUS_EXPLAIN[status]}
    </p>
  );
}

/** 6. Từ điển nhanh cuối trang chủ. */
export function GuideGlossary() {
  const { guest } = useApp();
  if (!guest) return null;
  return (
    <section className="guide-glossary dash-wide" aria-labelledby="guide-glossary-title">
      <h2 id="guide-glossary-title">Từ điển nhanh</h2>
      <dl>
        {GUIDE_GLOSSARY.map((item) => (
          <div key={item.term}>
            <dt>{item.term}</dt>
            <dd>{item.text}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** 7. Thẻ "Bạn vừa đi hết quy trình": khi lần chạy khách tự tạo đầu tiên được duyệt xong. */
function DoneCard() {
  return (
    <section className="guide-done" aria-labelledby="guide-done-title">
      <Icon name="approve" size={28} weight="duotone" className="guide-done-icon" />
      <div className="guide-banner-text">
        <h2 id="guide-done-title">{GUIDE_DONE.title}</h2>
        <p>{GUIDE_DONE.text}</p>
      </div>
      <div className="guide-actions">
        <LoginButton label={GUIDE_DONE.login} />
        <Link href="/docs" className="btn guide-btn">
          {GUIDE_DONE.docs}
        </Link>
      </div>
    </section>
  );
}

const finishedByGuest = (run: { id: string; status: RunStatus }) =>
  run.id.startsWith(GUEST_RUN_PREFIX) && run.status === "approved";

export function HomeGuideDone() {
  const { guest, runs } = useApp();
  if (!guest || !(runs ?? []).some(finishedByGuest)) return null;
  return (
    <div className="dash-wide">
      <DoneCard />
    </div>
  );
}

export function RunGuideDone() {
  const { guest } = useApp();
  const { detail } = useRun();
  if (!guest || !detail || !finishedByGuest(detail.record)) return null;
  return <DoneCard />;
}
