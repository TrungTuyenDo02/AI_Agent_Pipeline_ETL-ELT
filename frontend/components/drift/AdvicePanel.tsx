"use client";

import { useState } from "react";

import { ErrorBox } from "@/components/ui";
import { apiPost, messageOf } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/drift";
import type { Advice } from "@/lib/types";

// Đề xuất sửa pipeline cho một thay đổi: file nào, sửa gì. Phần chắc chắn do code dựng; Gemini chỉ diễn giải thêm khi bạn bấm.

export function AdvicePanel({ changeId, runId }: { changeId: number; runId?: string }) {
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load(useAi: boolean) {
    setBusy(true);
    setError("");
    try {
      setAdvice(await apiPost<Advice>(`/schema-changes/${changeId}/suggest`, { run_id: runId ?? "", use_ai: useAi }));
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  }

  if (!advice) {
    return (
      <div className="stack" style={{ gap: 6 }}>
        <button type="button" className="btn small" disabled={busy} onClick={() => load(false)}>
          {busy ? "Đang phân tích…" : "Pipeline cần sửa gì?"}
        </button>
        {error && <ErrorBox message={error} />}
      </div>
    );
  }
  return (
    <div className={`advice ${advice.needs_pipeline_change ? "needs" : "fine"}`}>
      <strong>{advice.headline}</strong>
      {advice.files.length > 0 && (
        <ul className="advice-files">
          {advice.files.map((f) => (
            <li key={f.path} className={f.impact}>
              <span className="chip">{ROLE_LABELS[f.role] ?? f.role}</span>
              <span className="mono small">{f.path}</span>
              <span className="muted small">{f.impact === "direct" ? "sửa trực tiếp" : "bị ảnh hưởng"}</span>
            </li>
          ))}
        </ul>
      )}
      {advice.actions.length > 0 && (
        <ol className="advice-actions">
          {advice.actions.map((a) => (
            <li key={a.where + a.what}>
              <span className="mono small">{a.where}</span>
              <div>{a.what}</div>
            </li>
          ))}
        </ol>
      )}
      {advice.ai_text && (
        <div className="advice-ai">
          <span className="badge info">{advice.ai_source === "gemini" ? "Gemini" : "AI (mô phỏng)"}</span>
          <p style={{ whiteSpace: "pre-line" }}>{advice.ai_text}</p>
        </div>
      )}
      {advice.ai_source === "unavailable" && (
        <p className="muted small">Chưa gọi được AI; phần trên do hệ thống phân tích.</p>
      )}
      {!advice.ai_text && (advice.files.length > 0 || advice.actions.length > 0) && (
        <button type="button" className="btn small" disabled={busy} onClick={() => load(true)}>
          {busy ? "Đang hỏi AI…" : "Hỏi AI diễn giải thêm"}
        </button>
      )}
      {error && <ErrorBox message={error} />}
    </div>
  );
}
