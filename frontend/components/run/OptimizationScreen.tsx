"use client";

import { formatNumber, formatPct, formatUsd } from "@/lib/format";
import type { Optimization } from "@/lib/types";

import { CodeDiff } from "../CodeDiff";
import { SampleTag } from "../GuestBar";
import { GuideNote } from "../guide/Guide";
import { Card, Empty, PassMark } from "../ui";
import { useRun } from "./RunContext";

/** Thẻ so sánh Trước / Sau (CLAUDE.md yêu cầu 6): mọi số do code đo (V3), không do LLM nói. */
function BeforeAfter({ report }: { report: Optimization }) {
  const applied = report.decision === "applied";
  const checks = report.equivalence ?? [];
  const same = checks.filter((c) => c.equal).length;
  const gain = report.improvement_pct;
  const before = report.before?.median_ms;
  const after = report.after?.median_ms;
  const correct = checks.length === 0 ? "Chưa đối chiếu" : same === checks.length ? "Giống bản gốc" : "Khác bản gốc";
  return (
    <section className="card before-after" aria-labelledby="ba-title">
      <header className="card-head">
        <h2 id="ba-title">
          So sánh trước / sau tối ưu <SampleTag />
        </h2>
        <span className={applied ? "badge ok" : "badge muted"}>{applied ? "Đã áp dụng bản mới" : "Giữ bản gốc"}</span>
      </header>
      <div className="ba-body">
        <div className="ba-hero">
          <strong className={gain == null ? "ba-big flat" : gain > 0 ? "ba-big up" : "ba-big"}>
            {gain != null ? `${gain > 0 ? "−" : "+"}${formatPct(Math.abs(gain))}` : "Không đổi"}
          </strong>
          <span>
            {gain != null
              ? gain > 0
                ? "thời gian chạy giảm"
                : "thời gian chạy tăng"
              : "không có bản tối ưu đạt yêu cầu, giữ bản gốc"}
          </span>
        </div>
        <table className="figures ba-table">
          <thead>
            <tr>
              <th>Chỉ số</th>
              <th className="num">Trước</th>
              <th className="num">Sau</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Thời gian chạy (trung vị)</td>
              <td className="num">{before != null ? `${formatNumber(before)} ms` : "—"}</td>
              <td className="num">{after != null ? `${formatNumber(after)} ms` : "—"}</td>
            </tr>
            <tr>
              <td>
                Chi phí máy mỗi lần chạy
                <small className="muted ba-note">tỉ lệ theo thời gian chạy</small>
              </td>
              <td className="num">100%</td>
              <td className="num">{before && after != null ? formatPct((100 * after) / before) : "—"}</td>
            </tr>
            <tr>
              <td>Độ đúng kết quả</td>
              <td className="num">bản gốc</td>
              <td className="num">
                <span className={checks.length && same === checks.length ? "badge ok" : "badge warn"}>
                  {correct}
                  {checks.length > 0 && ` (${same}/${checks.length} bộ dữ liệu)`}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="small">
        <strong>Lý do:</strong> {report.reason || "—"}
      </p>
      <small className="muted">
        Chi phí gọi LLM để tối ưu: {formatUsd(report.llm_cost_usd)} · {report.attempts ?? 0} lần thử · đo 1 lần khởi
        động + {report.before?.runs ?? "N"} lần, lấy trung vị. Chỉ áp dụng khi kết quả giống hệt trên mọi bộ và đạt
        ngưỡng lợi ích.
      </small>
    </section>
  );
}

function Equivalence({ report }: { report: Optimization }) {
  const checks = report.equivalence ?? [];
  return (
    <Card title="Đối chiếu kết quả hai chiều">
      {checks.length === 0 && <Empty>Không có bản viết lại nào cần đối chiếu.</Empty>}
      <ul className="measured-list">
        {checks.map((check) => (
          <li key={check.dataset}>
            <PassMark passed={check.equal} />
            <span>
              <strong className="mono">{check.dataset}</strong>: {check.detail}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Findings({ report }: { report: Optimization }) {
  return (
    <Card title="Dấu hiệu chậm (sqlglot + EXPLAIN)">
      {!report.findings?.length && <Empty>Không phát hiện dấu hiệu chậm.</Empty>}
      <ul className="plain">
        {report.findings?.map((finding) => (
          <li key={finding.rule}>
            <span className="mono">{finding.rule}</span>: {finding.message}
          </li>
        ))}
      </ul>
      {report.explanation && (
        <div style={{ marginTop: 12 }}>
          <h3>
            LLM giải thích <span className="badge muted">chưa kiểm chứng</span>
          </h3>
          <p className="claimed-box">{report.explanation}</p>
        </div>
      )}
      {report.warehouse_hints && report.warehouse_hints.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h3>Gợi ý cho kho khác (không thực thi)</h3>
          <ul className="plain muted">
            {report.warehouse_hints.map((hint) => (
              <li key={hint}>{hint}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export function OptimizationScreen() {
  const { detail } = useRun();
  if (!detail) return null;
  const report = detail.optimization;
  if (!report.original_sql) {
    return (
      <>
        <GuideNote id="optimize" />
        <Card title="Tối ưu query">
          <Empty>Chưa tới bước tối ưu (E4 chạy sau khi code qua sandbox).</Empty>
        </Card>
      </>
    );
  }
  return (
    <>
      <GuideNote id="optimize" />
      <BeforeAfter report={report} />
      <div className="grid-2">
        <Equivalence report={report} />
        <Findings report={report} />
      </div>
      <Card title="SQL bảng đích: bản gốc ↔ bản đề xuất">
        {report.proposed_sql ? (
          <CodeDiff path="target.sql" original={report.original_sql} modified={report.proposed_sql} />
        ) : (
          <Empty>Không có bản đề xuất (giữ nguyên bản gốc).</Empty>
        )}
      </Card>
    </>
  );
}
