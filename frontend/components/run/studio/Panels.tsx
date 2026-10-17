"use client";

import Link from "next/link";

import { formatNumber, formatUsd } from "@/lib/format";
import type { RunDetail } from "@/lib/types";

import { ArrowRightIcon, ChartIcon, CpuIcon, DatabaseIcon, FlowIcon, LayersIcon } from "../../icons";
import { useRun } from "../RunContext";
import { SampleTag } from "../../GuestBar";
import { formatSeconds } from "./LiveNode";

// Ngăn "Chi tiết kỹ thuật" của màn Studio. Mọi số lấy từ API (đo thật); chưa đo → "—", LLM mock → "mô phỏng".

function PanelHead({ icon, title, aside }: { icon: React.ReactNode; title: string; aside?: React.ReactNode }) {
  return (
    <header className="panel-head">
      <span className="row">
        <span className="panel-icon">{icon}</span>
        <h2>{title}</h2>
      </span>
      {aside}
    </header>
  );
}

export function MetricsPanel({ detail }: { detail: RunDetail }) {
  const rows = detail.usage?.rows ?? [];
  const simulated = detail.usage?.simulated ?? detail.record.summary.simulated;
  const sum = (key: "input_tokens" | "output_tokens" | "cost_usd" | "seconds" | "calls") =>
    rows.reduce((total, row) => total + row[key], 0);
  const tokens = rows.length ? sum("input_tokens") + sum("output_tokens") : null;
  const sandbox = detail.sandbox ?? {};
  const cache = detail.usage?.cache_hit_rate;
  const stats = [
    { label: "Token LLM", value: simulated ? "mô phỏng" : formatNumber(tokens), sub: `${sum("calls")} lượt gọi` },
    {
      label: "Chi phí ước tính",
      value: simulated ? "mô phỏng" : rows.length ? formatUsd(sum("cost_usd")) : "—",
      sub: "theo bảng giá",
    },
    {
      label: "Thời gian LLM",
      value: simulated ? "mô phỏng" : rows.length ? formatSeconds(sum("seconds")) : "—",
      sub: "tổng các lượt gọi",
    },
    {
      label: "Test chạy thử",
      value: sandbox.tests_total ? `${sandbox.tests_ok}/${sandbox.tests_total}` : "—",
      sub: "V2 đo bằng dbt",
    },
    {
      label: "Trúng cache",
      value: simulated ? "mô phỏng" : cache === null || cache === undefined ? "—" : `${Math.round(cache * 100)}%`,
      sub: "token đầu vào",
    },
    { label: "Vòng sửa lỗi", value: String(detail.record.summary.fix_attempts ?? 0), sub: "sau lỗi V1/V2" },
  ];
  return (
    <section className="card panel">
      <PanelHead icon={<ChartIcon />} title="Chỉ số đo được" aside={<SampleTag />} />
      <div className="metric-grid">
        {stats.map((stat) => (
          <div key={stat.label} className="metric">
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
            <small>{stat.sub}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

export function FlowPanel({ detail }: { detail: RunDetail }) {
  const { runId } = useRun();
  const sources = detail.spec.sources ?? [];
  const target = detail.spec.target;
  const flowing = detail.busy;
  const rows = detail.sandbox?.target_rows;
  return (
    <section className="card panel">
      <PanelHead
        icon={<FlowIcon />}
        title="Luồng dữ liệu"
        aside={
          <Link href={`/runs/${runId}/catalog`} className="small">
            Chi tiết <ArrowRightIcon size={14} />
          </Link>
        }
      />
      {!target ? (
        <p className="empty">Hiện khi có kế hoạch.</p>
      ) : (
        <div className="flow" data-flowing={flowing}>
          <div className="flow-col">
            {sources.length === 0 && <div className="flow-node muted">—</div>}
            {sources.map((source) => (
              <div key={source.name} className="flow-node" title={source.name}>
                <span className="flow-icon">
                  <DatabaseIcon size={14} />
                </span>
                <span>
                  <strong className="mono">{source.name}</strong>
                  <small>{source.kind}</small>
                </span>
              </div>
            ))}
          </div>
          <div className="flow-link" aria-hidden />
          <div className="flow-col">
            <div className="flow-node agent">
              <span className="flow-tag">{detail.spec.mode?.toUpperCase() ?? "dbt"}</span>
              <span className="flow-icon">
                <CpuIcon size={14} />
              </span>
              <span>
                <strong>dbt staging → mart</strong>
                <small>{sources.length} model staging</small>
              </span>
            </div>
          </div>
          <div className="flow-link" aria-hidden />
          <div className="flow-col">
            <div className="flow-node" title={target}>
              <span className="flow-icon">
                <LayersIcon size={14} />
              </span>
              <span>
                <strong className="mono">{target}</strong>
                <small>{rows === undefined ? "chưa chạy thử" : `${formatNumber(rows)} dòng (sandbox)`}</small>
              </span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
