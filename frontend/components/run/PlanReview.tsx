"use client";

import { useState } from "react";

import type { OptionChoice, PipelineOptions, PlanPending, PlanStep, Spec } from "@/lib/types";

import { useHasRole } from "../AppContext";
import { RoleNote } from "../Topbar";
import { ErrorBox } from "../ui";
import { useRun } from "./RunContext";

export function PlanSteps({ steps }: { steps: PlanStep[] }) {
  return (
    <ol className="plan-steps">
      {steps.map((step, index) => (
        <li key={`${index}-${step.title}`}>
          <span className="plan-index" aria-hidden>
            {index + 1}
          </span>
          <div>
            <strong>{step.title}</strong>
            {step.detail && <p>{step.detail}</p>}
            {step.reason && (
              <p className="plan-reason">
                <span>Vì sao:</span> {step.reason}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function SpecGlance({ spec, sources }: { spec: Spec; sources: string[] }) {
  return (
    <dl className="kv">
      <dt>Bảng đích</dt>
      <dd className="mono">{spec.target}</dd>
      <dt>Đọc từ</dt>
      <dd className="mono">{sources.join(", ") || "—"}</dd>
      <dt>Mỗi dòng là</dt>
      <dd className="mono">{spec.grain?.join(", ") || "—"}</dd>
      <dt>Cột đầu ra</dt>
      <dd className="mono">{spec.output_columns?.map((c) => `${c.name} (${c.type})`).join(", ") || "—"}</dd>
      <dt>Kiểu pipeline</dt>
      <dd>
        {spec.mode} — {spec.mode_reason}
      </dd>
      <dt>Giả định</dt>
      <dd>
        {spec.assumptions?.length ? (
          <ul className="plain">
            {spec.assumptions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          "—"
        )}
      </dd>
    </dl>
  );
}

interface Picked {
  load_mode: string;
  schedule: string;
  incremental_column: string;
}

function OptionGroup({
  legend,
  name,
  choices,
  value,
  reason,
  onChange,
  disabled,
}: {
  legend: string;
  name: string;
  choices: OptionChoice[];
  value: string;
  reason: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <fieldset>
      <legend>{legend}</legend>
      <div className="option-pills">
        {choices.map((choice) => (
          <label key={choice.value} className="option">
            <input
              type="radio"
              name={name}
              value={choice.value}
              checked={value === choice.value}
              disabled={disabled}
              onChange={() => onChange(choice.value)}
            />
            <span>{choice.label}</span>
          </label>
        ))}
      </div>
      <p className="muted small">{reason}</p>
    </fieldset>
  );
}

/** Lựa chọn pipeline (nạp, lịch chạy, kết nối): mặc định là đề xuất của code kèm lý do; DE đổi nếu muốn. */
function PipelineChoices({
  options,
  pending,
  picked,
  setPicked,
  disabled,
}: {
  options: PipelineOptions;
  pending: PlanPending;
  picked: Picked;
  setPicked: (next: Picked) => void;
  disabled: boolean;
}) {
  const choices = pending.option_choices;
  if (!choices) return null;
  const columns = pending.time_columns ?? [];
  return (
    <div className="stack" style={{ gap: 10 }}>
      <h3>Lựa chọn pipeline</h3>
      <OptionGroup
        legend="Cách nạp dữ liệu"
        name="load_mode"
        choices={choices.load_mode}
        value={picked.load_mode}
        reason={options.load_reason}
        disabled={disabled}
        onChange={(value) => setPicked({ ...picked, load_mode: value })}
      />
      {picked.load_mode === "incremental" && (
        <label>
          <span>Cột thời gian để biết phần mới</span>
          <select
            value={picked.incremental_column}
            disabled={disabled}
            onChange={(e) => setPicked({ ...picked, incremental_column: e.target.value })}
          >
            <option value="">— chọn cột —</option>
            {columns.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      )}
      <OptionGroup
        legend="Lịch chạy (chỉ ghi vào DAG, không chạy thật)"
        name="schedule"
        choices={choices.schedule}
        value={picked.schedule}
        reason={options.schedule_reason}
        disabled={disabled}
        onChange={(value) => setPicked({ ...picked, schedule: value })}
      />
      <div>
        <strong>Cách lấy dữ liệu</strong>
        <ul className="plain">
          {options.connections.map((c) => (
            <li key={c.source}>
              <span className="mono">{c.source}</span>: {c.via}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function PlanReview({ pending }: { pending: PlanPending }) {
  const { act } = useRun();
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const engineer = useHasRole("engineer");
  const options = pending.spec.options;
  const [picked, setPicked] = useState<Picked>({
    load_mode: options?.load_mode ?? "full",
    schedule: options?.schedule ?? "daily",
    incremental_column: options?.incremental_column ?? "",
  });

  async function decide(decision: "approve" | "revise") {
    setSending(true);
    setError(
      await act(
        "/plan",
        { decision, note, options: options ? picked : undefined },
        decision === "approve"
          ? "Đã duyệt kế hoạch, agent bắt đầu sinh code."
          : "Đã gửi góp ý, agent lập lại kế hoạch.",
      ),
    );
    setSending(false);
  }

  return (
    <div className="stack" style={{ gap: 14 }}>
      <RoleNote need="engineer" />
      <p className="plan-summary">{pending.summary}</p>
      <div className="grid-2">
        <div>
          <h3 className="row">
            Các bước agent sẽ làm <span className="badge muted">LLM lập, bạn kiểm tra</span>
          </h3>
          <PlanSteps steps={pending.steps} />
        </div>
        <div>
          <h3>Đặc tả</h3>
          <SpecGlance spec={pending.spec} sources={pending.sources} />
        </div>
      </div>
      {options && (
        <PipelineChoices
          options={options}
          pending={pending}
          picked={picked}
          setPicked={setPicked}
          disabled={sending || !engineer}
        />
      )}
      <div className="alert info">
        <span>{pending.next_steps}</span>
      </div>
      <label htmlFor="plan-note">Muốn sửa? Ghi rõ cần thay đổi gì (agent sẽ lập lại kế hoạch)</label>
      <textarea
        id="plan-note"
        rows={3}
        maxLength={2000}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Ví dụ: thêm cột kênh bán; loại đơn hoàn tiền khỏi doanh thu"
      />
      {error && <ErrorBox message={error} />}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button
          type="button"
          className="btn danger"
          disabled={sending || !engineer || !note.trim()}
          onClick={() => decide("revise")}
        >
          Yêu cầu sửa kế hoạch
        </button>
        <button type="button" className="btn ok" disabled={sending || !engineer} onClick={() => decide("approve")}>
          Đồng ý, sinh code
        </button>
      </div>
    </div>
  );
}
