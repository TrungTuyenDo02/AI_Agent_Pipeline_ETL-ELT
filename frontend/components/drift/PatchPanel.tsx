"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useToast } from "@/components/Toast";
import { ErrorBox, Loading } from "@/components/ui";
import { apiPost, messageOf } from "@/lib/api";
import { PATCH_ACTIONS } from "@/lib/drift";
import type { Accepted, PatchPlan } from "@/lib/types";

// Kế hoạch bản vá: hệ thống dựng bằng code (0 token) cái gì tự sửa, cái gì cần AI, cái gì cần bạn chọn. Bản vá không lập kế hoạch
// lại và không hỏi lại điều đã trả lời: nó mang đặc tả và code của lần chạy gốc.

export function PatchPanel({ runId, onClose }: { runId: string; onClose: () => void }) {
  const router = useRouter();
  const toast = useToast();
  const [plan, setPlan] = useState<PatchPlan | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const preview = useCallback(
    async (next: Record<string, string>) => {
      setError("");
      try {
        setPlan(await apiPost<PatchPlan>(`/runs/${runId}/patch-plan`, { answers: next }));
      } catch (exc) {
        setError(messageOf(exc));
      }
    },
    [runId],
  );

  useEffect(() => {
    const first = setTimeout(() => void preview({}), 0);
    return () => clearTimeout(first);
  }, [preview]);

  function choose(id: string, value: string) {
    const next = { ...answers, [id]: value };
    setAnswers(next);
    void preview(next);
  }

  async function create() {
    setBusy(true);
    setError("");
    try {
      const accepted = await apiPost<Accepted>(`/runs/${runId}/patch`, { answers });
      toast("Đã tạo lần chạy bản vá.");
      router.push(`/runs/${accepted.run_id}`);
    } catch (exc) {
      setError(messageOf(exc));
      setBusy(false);
    }
  }

  return (
    <div className="patch-panel">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <strong>Kế hoạch bản vá</strong>
        <button type="button" className="btn small" onClick={onClose}>
          Đóng
        </button>
      </div>
      {!plan && !error && <Loading text="Đang lập kế hoạch vá…" lines={2} />}
      {plan && (
        <>
          <ul className="patch-items">
            {plan.items.map((item) => {
              const action = PATCH_ACTIONS[item.action];
              return (
                <li key={item.change_id} className={`patch-item ${item.action}`}>
                  <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <span className={`badge ${action.tone}`}>{action.label}</span>
                    <span className="mono small">
                      {item.table}
                      {item.column ? `.${item.column}` : ""}
                    </span>
                  </div>
                  <p className="small">{item.summary}</p>
                  {item.files.length > 0 && <p className="muted small mono">{item.files.join(" · ")}</p>}
                  {item.question && (
                    <fieldset className="patch-question">
                      <legend className="small">{item.question.text}</legend>
                      <div className="stack" style={{ gap: 4 }}>
                        {item.question.options.map((option) => (
                          <label key={option.value} className="option">
                            <input
                              type="radio"
                              name={`patch-${item.change_id}`}
                              value={option.value}
                              checked={answers[item.question!.id] === option.value}
                              onChange={() => choose(item.question!.id, option.value)}
                            />
                            <span>{option.label}</span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  )}
                </li>
              );
            })}
          </ul>
          <p className="small">
            <strong>Ước tính:</strong> {plan.estimate}
          </p>
          <p className="muted small">
            Bản vá dùng lại kế hoạch bạn đã duyệt, không hỏi lại. Sửa xong vẫn chạy kiểm tra, so bảng đích với lần chạy
            gốc và chờ bạn duyệt ở J2.
          </p>
          <button type="button" className="btn primary" disabled={!plan.ready || busy} onClick={create}>
            {busy ? "Đang tạo…" : "Tạo bản vá"}
          </button>
        </>
      )}
      {error && <ErrorBox message={error} />}
    </div>
  );
}
