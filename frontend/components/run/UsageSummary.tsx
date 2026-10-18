"use client";

import { formatNumber, formatPct, formatUsd } from "@/lib/format";

import { useApp } from "../AppContext";
import { SampleTag } from "../GuestBar";
import { Icon } from "../icons";
import { Empty, Stat } from "../ui";
import { useRun } from "./RunContext";

// Khối "Token, chi phí và thời gian" luôn hiện ở màn tổng quan lần chạy (không nằm trong ngăn thu gọn).
// Mọi số lấy từ API (đo thật); lần chạy dùng LLM mô phỏng thì ghi "mô phỏng", chưa đo thì "—".

const TASK_LABELS: Record<string, string> = {
  input_gate: "Kiểm tra đầu vào",
  planner: "Lập kế hoạch",
  codegen: "Sinh code",
  testgen: "Sinh test",
  optimizer: "Tối ưu query",
};

function secondsText(value: number): string {
  return value < 60 ? `${value.toFixed(1)} s` : `${Math.floor(value / 60)} phút ${Math.round(value % 60)} s`;
}

export function UsageSummary() {
  const { detail } = useRun();
  const { guest } = useApp();
  if (!detail) return null;
  const usage = detail.usage;
  const rows = usage?.rows ?? [];
  const simulated = usage?.simulated ?? false;
  const show = (text: string) => (simulated ? "mô phỏng" : text);
  const sum = rows.reduce(
    (total, row) => ({
      calls: total.calls + row.calls,
      input: total.input + row.input_tokens,
      output: total.output + row.output_tokens,
      cost: total.cost + row.cost_usd,
      seconds: total.seconds + row.seconds,
    }),
    { calls: 0, input: 0, output: 0, cost: 0, seconds: 0 },
  );
  const machineSeconds = (detail.events ?? []).reduce((total, event) => total + event.seconds, 0);
  const models = [...new Set(rows.flatMap((row) => row.models ?? []))];
  const cache = usage?.cache_hit_rate;
  return (
    <section className="card usage-summary" aria-label="Token, chi phí và thời gian">
      <header className="card-head">
        <h2 className="row">
          <Icon name="cost" size={20} weight="duotone" /> Token, chi phí và thời gian
        </h2>
        {simulated ? (
          <span className="badge warn" title="LLM_PROVIDER=mock: câu trả lời cố định, không tốn tiền">
            Mô phỏng
          </span>
        ) : guest ? (
          <SampleTag />
        ) : (
          <span className="badge muted">Ước tính theo bảng giá công khai</span>
        )}
      </header>
      <div className="card-body stack" style={{ gap: 12 }}>
        <div className="stats">
          <Stat
            label="Chi phí LLM"
            value={show(rows.length ? formatUsd(sum.cost) : "—")}
            hint="Tổng các lượt gọi LLM"
          />
          <Stat
            label="Token vào / ra"
            value={show(rows.length ? `${formatNumber(sum.input)} / ${formatNumber(sum.output)}` : "—")}
          />
          <Stat label="Lượt gọi LLM" value={rows.length ? sum.calls : "—"} />
          <Stat
            label="Thời gian LLM"
            value={show(rows.length ? secondsText(sum.seconds) : "—")}
            hint="Tổng thời gian chờ LLM trả lời"
          />
          <Stat
            label="Thời gian máy chạy"
            value={machineSeconds > 0 ? secondsText(machineSeconds) : "—"}
            hint="Cộng thời gian các bước đã xong (không tính lúc chờ người). Chỉ giữ trong phiên máy chủ hiện tại."
          />
          <Stat
            label="Trúng cache"
            value={show(cache == null ? "—" : formatPct(Math.round(cache * 1000) / 10))}
            hint="Phần token đầu vào nhà cung cấp lấy từ cache"
          />
        </div>
        {models.length > 0 && (
          <p className="small muted usage-models">
            Model đã trả lời:{" "}
            {models.map((model) => (
              <span key={model} className="badge muted mono">
                {model}
              </span>
            ))}
          </p>
        )}
        {rows.length === 0 ? (
          <Empty>Lần chạy chưa gọi LLM, nên chưa có token và chi phí.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="figures">
              <thead>
                <tr>
                  <th>Bước</th>
                  <th>Model</th>
                  <th className="num">Lượt</th>
                  <th className="num">Token vào</th>
                  <th className="num">Token ra</th>
                  <th className="num">Chi phí</th>
                  <th className="num">Thời gian</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.task}>
                    <td>{TASK_LABELS[row.task] ?? row.task}</td>
                    <td className="mono small">{(row.models ?? []).join(", ") || "—"}</td>
                    <td className="num">{row.calls}</td>
                    <td className="num">{show(formatNumber(row.input_tokens))}</td>
                    <td className="num">{show(formatNumber(row.output_tokens))}</td>
                    <td className="num">{show(formatUsd(row.cost_usd))}</td>
                    <td className="num">{show(secondsText(row.seconds))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <small className="muted">
          Chi phí chỉ gồm các lượt gọi LLM đã trả kết quả; lượt bị lỗi hoặc quá hạn có thể vẫn bị nhà cung cấp tính tiền
          nhưng chưa được ghi lại.
        </small>
      </div>
    </section>
  );
}
