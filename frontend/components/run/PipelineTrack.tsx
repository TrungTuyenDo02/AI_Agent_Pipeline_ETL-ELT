"use client";

import { useState } from "react";

import type { Stage, StageState } from "@/lib/types";

import { DrawnCheck, Icon, SpinningIcon } from "../icons";
import { useRun } from "./RunContext";

const STATE_TEXT: Record<StageState, string> = {
  waiting: "chưa tới",
  running: "đang chạy",
  passed: "đạt",
  failed: "lỗi",
  human: "chờ bạn",
};

/** Ai làm bước này: nhãn chữ đi kèm hình dạng (không chỉ dựa vào hình/màu). */
const ACTOR: Record<Stage["kind"], string> = { E: "Agent", V: "Tự động", J: "Bạn" };

/** 13 bước gom thành 4 giai đoạn dễ hiểu (id bước khớp src/agents/stages.py). */
const PHASES: { id: string; label: string; stages: string[] }[] = [
  { id: "understand", label: "Hiểu yêu cầu", stages: ["planner", "clarify", "spec_check", "plan_review"] },
  { id: "build", label: "Soạn code", stages: ["prepare", "schema", "codegen", "testgen"] },
  { id: "verify", label: "Kiểm tra", stages: ["safety", "sandbox", "rescue", "optimizer", "compare"] },
  { id: "review", label: "Duyệt", stages: ["review"] },
];

/** Trạng thái giai đoạn: lỗi > chờ bạn > đang chạy > xong hết > chưa tới. */
function phaseState(stages: Stage[]): StageState {
  for (const state of ["failed", "human", "running"] as const) if (stages.some((s) => s.state === state)) return state;
  return stages.length > 0 && stages.every((s) => s.state === "passed") ? "passed" : "waiting";
}

/** Icon trong vòng tròn bước (CLAUDE.md 9.11): đang chạy = CircleNotch xoay, xong = dấu tích tự vẽ, lỗi/chờ bạn = icon. */
function StateIcon({ state, size = 14 }: { state: StageState; size?: number }) {
  if (state === "running") return <SpinningIcon size={size} />;
  if (state === "passed") return <DrawnCheck size={size} />;
  if (state === "waiting") return null;
  return <Icon name={state === "failed" ? "close" : "awaitingReview"} size={size} weight="bold" />;
}

function SubStep({ stage }: { stage: Stage }) {
  const title = `Mã ${stage.code} · ${ACTOR[stage.kind]} · ${STATE_TEXT[stage.state]}${stage.detail ? ` — ${stage.detail}` : ""}`;
  return (
    <li
      className="stage"
      data-kind={stage.kind}
      data-state={stage.state}
      title={title}
      aria-current={stage.state === "running" || stage.state === "human" ? "step" : undefined}
    >
      <span className="stage-dot">
        {/* key theo trạng thái: hiệu ứng chỉ chạy khi bước đổi trạng thái */}
        <span className="stage-icon" key={stage.state}>
          <StateIcon state={stage.state} />
        </span>
      </span>
      <span className="stage-label">{stage.label}</span>
      <span className="stage-actor">{ACTOR[stage.kind]}</span>
      <span className="sr-only">{STATE_TEXT[stage.state]}</span>
    </li>
  );
}

/** Tiến trình 4 giai đoạn; trạng thái từng bước do máy chủ suy từ dữ liệu thật. Bấm giai đoạn để xem bước con. */
export function PipelineTrack() {
  const { detail } = useRun();
  const [opened, setOpened] = useState<string | null | undefined>(undefined); // undefined = tự mở giai đoạn đang làm
  const stages = detail?.stages ?? [];
  if (stages.length === 0) return null;
  const phases = PHASES.map((phase) => {
    const items = phase.stages.flatMap((id) => stages.filter((s) => s.id === id));
    const done = items.filter((s) => s.state === "passed").length;
    return { ...phase, items, done, state: phaseState(items) };
  }).filter((phase) => phase.items.length > 0);
  const active = phases.find((p) => p.state === "failed" || p.state === "human" || p.state === "running")?.id ?? null;
  const open = opened === undefined ? active : opened;
  const current = phases.find((p) => p.id === open);
  const total = phases.reduce((sum, p) => sum + p.items.length, 0);
  const finished = phases.reduce((sum, p) => sum + p.done, 0);
  const percent = total > 0 ? Math.round((finished / total) * 100) : 0;
  const overallState = phases.some((p) => p.state === "failed")
    ? "failed"
    : phases.some((p) => p.state === "human")
      ? "human"
      : finished === total
        ? "passed"
        : "running";
  const currentPhase = phases.find((p) => p.id === active);
  return (
    <section className="pipeline" aria-label="Tiến trình">
      <div className="overall" data-state={overallState}>
        <div className="overall-text">
          <strong>
            {overallState === "passed"
              ? "Đã xong tất cả các bước"
              : overallState === "failed"
                ? `Dừng ở giai đoạn “${currentPhase?.label ?? ""}”`
                : overallState === "human"
                  ? `Đang chờ bạn ở giai đoạn “${currentPhase?.label ?? ""}”`
                  : currentPhase
                    ? `Đang ở giai đoạn “${currentPhase.label}”`
                    : "Đang chuẩn bị"}
          </strong>
          <span className="muted">
            {finished}/{total} bước · {percent}%
          </span>
        </div>
        <div
          className="overall-bar"
          role="progressbar"
          aria-label="Tiến độ toàn bộ lần chạy"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <span style={{ width: `${percent}%` }} />
        </div>
      </div>
      <ol className="phase-track">
        {phases.map((phase, index) => (
          <li
            key={phase.id}
            className={index > 0 && phases[index - 1].state === "passed" ? "phase after-passed" : "phase"}
            data-state={phase.state}
          >
            <button
              type="button"
              className="phase-btn"
              aria-expanded={phase.id === open}
              aria-controls="phase-steps"
              onClick={() => setOpened(phase.id === open ? null : phase.id)}
              title={`${phase.label}: ${STATE_TEXT[phase.state]} — bấm để ${phase.id === open ? "đóng" : "xem"} các bước`}
            >
              <span className="phase-dot">
                <span className="stage-icon" key={phase.state}>
                  <StateIcon state={phase.state} size={16} />
                </span>
              </span>
              <span className="phase-label">{phase.label}</span>
              <span className="phase-meta">
                {phase.state === "failed"
                  ? "Có lỗi"
                  : phase.state === "human"
                    ? "Chờ bạn"
                    : phase.state === "running"
                      ? "Đang chạy"
                      : `${phase.done}/${phase.items.length} bước`}
              </span>
            </button>
          </li>
        ))}
      </ol>
      {current && (
        <div className="phase-steps" id="phase-steps">
          <p className="small muted">Các bước của giai đoạn “{current.label}”</p>
          <ol className="pipeline-track">
            {current.items.map((stage) => (
              <SubStep key={stage.id} stage={stage} />
            ))}
          </ol>
        </div>
      )}
      <div className="pipeline-legend">
        <span title="Agent thực thi (gọi LLM)">
          <i className="e" />
          Agent
        </span>
        <span title="Code tự kiểm chứng, không gọi LLM">
          <i className="v" />
          Tự động
        </span>
        <span title="Con người quyết định">
          <i className="j" />
          Bạn
        </span>
      </div>
    </section>
  );
}
