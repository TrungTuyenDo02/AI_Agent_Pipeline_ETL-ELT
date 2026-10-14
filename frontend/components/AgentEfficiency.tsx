"use client";

import { useState } from "react";

import type { RunRecord } from "@/lib/types";
import { formatNumber, formatPct, formatUsd } from "@/lib/format";

import { useApp } from "./AppContext";
import { Icon } from "./icons";

// Hiệu quả agent trên các lần chạy đã có (để cân nhắc có nên dùng rộng rãi). Chỉ tính lần chạy LLM thật;
// lần chạy mô phỏng chỉ được đếm riêng. Các ô nhập là GIẢ ĐỊNH của người dùng, không phải số đo.

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function positive(text: string): number | null {
  const value = Number(text.replace(",", "."));
  return Number.isFinite(value) && value > 0 ? value : null;
}

export function summarizeRuns(runs: RunRecord[]) {
  const real = runs.filter((run) => !run.summary.simulated);
  const finished = real.filter((run) => run.status === "approved" || run.status === "failed");
  const approved = real.filter((run) => run.status === "approved");
  const costs = real.map((run) => run.summary.cost_usd ?? 0).filter((cost) => cost > 0);
  return {
    total: runs.length,
    simulated: runs.length - real.length,
    real: real.length,
    approved: approved.length,
    failed: real.filter((run) => run.status === "failed").length,
    approvalRate: finished.length > 0 ? approved.length / finished.length : null,
    medianCost: median(costs),
    totalCost: costs.reduce((sum, cost) => sum + cost, 0),
    costPerApproved: approved.length > 0 ? costs.reduce((sum, cost) => sum + cost, 0) / approved.length : null,
    medianTokens: median(real.map((run) => run.summary.tokens ?? 0).filter((tokens) => tokens > 0)),
    medianFixes: median(real.map((run) => run.summary.fix_attempts ?? 0)),
    optimizedRate:
      real.length > 0 ? real.filter((run) => run.summary.optimization === "applied").length / real.length : null,
  };
}

export function AgentEfficiency() {
  const { runs } = useApp();
  const [perMonth, setPerMonth] = useState("100");
  const [manualMinutes, setManualMinutes] = useState("");
  const [reviewMinutes, setReviewMinutes] = useState("");
  const [hourly, setHourly] = useState("");
  if (!runs || runs.length === 0) return null;
  const s = summarizeRuns(runs);
  const months = positive(perMonth);
  const agentMonthly = s.costPerApproved != null && months != null ? s.costPerApproved * months : null;
  const manual = positive(manualMinutes);
  const review = positive(reviewMinutes) ?? 0;
  const rate = positive(hourly);
  const humanMonthly = manual != null && rate != null && months != null ? (manual / 60) * rate * months : null;
  const agentTotal =
    agentMonthly != null && rate != null && months != null ? agentMonthly + (review / 60) * rate * months : null;
  return (
    <details className="card efficiency" open>
      <summary>
        <Icon name="performance" size={20} weight="duotone" />
        <strong>Hiệu quả agent</strong>
        <span className="muted small">
          {s.real} lần chạy LLM thật{s.simulated > 0 ? ` · ${s.simulated} lần mô phỏng (không tính)` : ""}
        </span>
      </summary>
      <div className="efficiency-body">
        {s.real === 0 ? (
          <p className="muted">
            Chưa có lần chạy dùng LLM thật nên chưa tính được chi phí và tỉ lệ duyệt. Chạy với khóa API thật để có số
            đo.
          </p>
        ) : (
          <div className="stats">
            <div className="stat" title="Lần được duyệt / (lần được duyệt + lần lỗi)">
              <span>Tỉ lệ được duyệt</span>
              <strong>{s.approvalRate == null ? "—" : formatPct(Math.round(s.approvalRate * 1000) / 10)}</strong>
            </div>
            <div className="stat">
              <span>Chi phí trung vị / lần</span>
              <strong>{s.medianCost == null ? "—" : formatUsd(s.medianCost)}</strong>
            </div>
            <div className="stat" title="Tổng chi phí chia cho số lần được duyệt (tính cả lần lỗi và lần bị từ chối)">
              <span>Chi phí / lần được duyệt</span>
              <strong>{s.costPerApproved == null ? "—" : formatUsd(s.costPerApproved)}</strong>
            </div>
            <div className="stat">
              <span>Token trung vị / lần</span>
              <strong>{s.medianTokens == null ? "—" : formatNumber(Math.round(s.medianTokens))}</strong>
            </div>
            <div className="stat">
              <span>Vòng sửa lỗi trung vị</span>
              <strong>{s.medianFixes == null ? "—" : s.medianFixes}</strong>
            </div>
            <div className="stat">
              <span>Có tối ưu được áp dụng</span>
              <strong>{s.optimizedRate == null ? "—" : formatPct(Math.round(s.optimizedRate * 1000) / 10)}</strong>
            </div>
          </div>
        )}
        <div className="efficiency-calc">
          <h3>Tính thử khi dùng rộng rãi</h3>
          <p className="small muted">
            Các ô dưới là <strong>giả định do bạn nhập</strong>, không phải số đo. Chưa có DE làm tay được đo thật để so
            sánh (quy trình: eval/baseline/PROTOCOL.md).
          </p>
          <div className="efficiency-inputs">
            <label>
              Số lần chạy / tháng
              <input inputMode="numeric" value={perMonth} onChange={(e) => setPerMonth(e.target.value)} />
            </label>
            <label>
              DE làm tay: phút / lần
              <input inputMode="numeric" value={manualMinutes} onChange={(e) => setManualMinutes(e.target.value)} />
            </label>
            <label>
              Reviewer duyệt: phút / lần
              <input inputMode="numeric" value={reviewMinutes} onChange={(e) => setReviewMinutes(e.target.value)} />
            </label>
            <label>
              Giá nhân công (USD / giờ)
              <input inputMode="decimal" value={hourly} onChange={(e) => setHourly(e.target.value)} />
            </label>
          </div>
          <ul className="efficiency-result">
            <li>
              Chi phí LLM mỗi tháng:{" "}
              <strong>
                {agentMonthly == null ? "chưa tính được (cần có lần được duyệt)" : formatUsd(agentMonthly)}
              </strong>
            </li>
            {humanMonthly != null && agentTotal != null && (
              <>
                <li>
                  DE làm tay: <strong>{formatUsd(humanMonthly)}</strong> / tháng · Agent (LLM + công duyệt):{" "}
                  <strong>{formatUsd(agentTotal)}</strong> / tháng
                </li>
                <li>
                  Chênh lệch:{" "}
                  <strong className={humanMonthly >= agentTotal ? "ok-text" : "fail-text"}>
                    {formatUsd(humanMonthly - agentTotal)}
                  </strong>{" "}
                  / tháng {humanMonthly >= agentTotal ? "(agent rẻ hơn)" : "(agent đắt hơn)"}
                </li>
              </>
            )}
          </ul>
          <p className="small muted">
            Chưa tính công sửa khi agent làm sai, chi phí hạ tầng và việc kiểm thử lại. Độ đúng còn hạn chế (ELT-Bench
            11/34 bảng), nên chỉ mở rộng khi tỉ lệ được duyệt và độ đúng thực tế đủ tốt.
          </p>
        </div>
      </div>
    </details>
  );
}
