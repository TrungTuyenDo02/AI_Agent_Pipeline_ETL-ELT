"use client";

import { formatNumber } from "@/lib/format";
import type { Bottleneck, PerfReport, Sandbox } from "@/lib/types";

import { Card, Empty } from "../ui";

const NOT_MEASURED = "chưa đo";

function ms(value: number | null | undefined): string {
  return value == null ? NOT_MEASURED : `${formatNumber(Math.round(value * 10) / 10)} ms`;
}

/** Ba con số khác nhau, không cộng dồn: tổng các model ≠ một lệnh dbt build ≠ cả DAG Airflow. */
function TimeFigures({ perf, sandbox, total }: { perf?: PerfReport | null; sandbox: Sandbox; total: number | null }) {
  const rows: [string, number | null | undefined, string][] = [
    ["Tổng thời gian các model", perf?.model_total_ms ?? total, "Cộng thời gian execute từng model"],
    [
      "Thời gian lệnh dbt build",
      perf?.dbt_wall_ms ?? sandbox.wall_ms,
      "Một invocation, các model có thể chạy song song",
    ],
    ["Thời gian toàn DAG (Airflow)", perf?.dag_wall_ms, "Chưa chạy Airflow thật trên sandbox"],
  ];
  return (
    <table className="figures">
      <tbody>
        {rows.map(([label, value, hint]) => (
          <tr key={label}>
            <td>
              {label}
              <small className="muted ba-note">{hint}</small>
            </td>
            <td className="num">{value == null ? <span className="badge muted">{NOT_MEASURED}</span> : ms(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Bảng thời gian mọi model (artifact dbt của lần chạy sandbox cuối). */
export function ModelTimings({ sandbox, perf }: { sandbox: Sandbox; perf?: PerfReport | null }) {
  const timings = [...(sandbox.model_timings ?? [])].sort((a, b) => (b.execute_ms ?? -1) - (a.execute_ms ?? -1));
  const measured = timings.filter((t) => t.execute_ms != null);
  const total = measured.length ? measured.reduce((sum, t) => sum + (t.execute_ms ?? 0), 0) : null;
  return (
    <Card title="Thời gian từng model">
      <TimeFigures perf={perf} sandbox={sandbox} total={total} />
      {timings.length === 0 ? (
        <Empty>Chưa đo: lần chạy này không có số đo từng model (dữ liệu cũ hoặc dbt không chạy xong).</Empty>
      ) : (
        <div className="table-wrap" role="region" aria-label="Thời gian từng model" tabIndex={0}>
          <table className="figures">
            <thead>
              <tr>
                <th>Model</th>
                <th>Trạng thái</th>
                <th>Kiểu lưu</th>
                <th className="num">Biên dịch</th>
                <th className="num">Chạy</th>
                <th className="num">Số dòng</th>
                <th className="num">% tổng</th>
              </tr>
            </thead>
            <tbody>
              {timings.map((t) => (
                <tr key={t.model}>
                  <td className="mono">{t.model}</td>
                  <td>{t.status}</td>
                  <td>{t.materialized || "—"}</td>
                  <td className="num">{ms(t.compile_ms)}</td>
                  <td className="num">{ms(t.execute_ms)}</td>
                  <td className="num">{t.rows == null ? NOT_MEASURED : formatNumber(t.rows)}</td>
                  <td className="num">
                    {t.execute_ms != null && total ? `${Math.round((100 * t.execute_ms) / total)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function Finding({ item }: { item: Bottleneck }) {
  if (!item.analyzed) {
    return (
      <li>
        <strong>
          #{item.rank} <span className="mono">{item.model}</span>
        </strong>{" "}
        <span className="badge warn">Chưa phân tích được</span>
        <p className="small muted">{item.unknown}</p>
      </li>
    );
  }
  return (
    <li>
      <strong>
        #{item.rank} <span className="mono">{item.model}</span>
      </strong>{" "}
      {item.operator && <span className="mono muted">{item.operator}</span>}
      <p className="small">
        <span className="badge ok">Đã đo</span> {item.phenomenon}
      </p>
      <ul className="plain small">
        {item.evidence?.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <p className="small">
        <span className="badge muted">Giả thuyết</span> {item.hypothesis} <em>Bước kiểm tra tiếp:</em> {item.next_step}
      </p>
      <p className="small muted">
        <span className="badge muted">Chưa kiểm chứng</span> {item.unknown}
      </p>
    </li>
  );
}

/** Điểm nghẽn: top N model chậm nhất phân tích bằng EXPLAIN ANALYZE (code, 0 token). */
export function Bottlenecks({ perf }: { perf?: PerfReport | null }) {
  return (
    <Card title="Điểm nghẽn">
      {!perf ? (
        <Empty>Chưa đo: lần chạy này chưa có báo cáo điểm nghẽn.</Empty>
      ) : !perf.measured ? (
        <Empty>{perf.note || "Chưa đo."}</Empty>
      ) : (
        <>
          <ul className="plain stack">
            {perf.findings?.map((item) => (
              <Finding key={`${item.rank}-${item.model}`} item={item} />
            ))}
          </ul>
          <small className="muted">
            Phân tích {perf.findings?.length ?? 0}/{perf.top_n ?? 0} model chậm nhất trên sandbox, tốn{" "}
            {ms(perf.analysis_ms)}, 0 token. Giả thuyết không được tính là lợi ích đã đạt.
          </small>
        </>
      )}
    </Card>
  );
}
