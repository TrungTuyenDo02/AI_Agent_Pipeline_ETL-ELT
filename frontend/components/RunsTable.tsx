"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { formatPct, formatTime, formatUsd } from "@/lib/format";
import { filterRuns, isRunFilter, RUN_FILTERS, runFilterHref, type RunFilterKey } from "@/lib/runFilters";
import type { RunRecord } from "@/lib/types";

import { useApp } from "./AppContext";
import { SampleTag } from "./GuestBar";
import { NEEDS_ACTION, runHref } from "./NotificationBell";
import { Icon } from "./icons";
import { StatusPill } from "./StatusPill";
import { Card, Empty, ErrorBox, Loading } from "./ui";

function RunRow({ run }: { run: RunRecord }) {
  const router = useRouter();
  const href = runHref(run);
  return (
    <tr className="clickable" onClick={() => router.push(href)}>
      <td>
        <Link href={href} className="truncate" title={run.request_text} onClick={(e) => e.stopPropagation()}>
          {run.request_text}
        </Link>
        <small className="muted mono">
          {run.id} · {run.requester}
        </small>
      </td>
      {/* data-label: tên cột hiện cạnh giá trị khi bảng xếp thành thẻ dọc trên điện thoại (CLAUDE.md 9.9) */}
      <td data-label="Trạng thái">
        <StatusPill status={run.status} />
        {run.pause_requested && <small className="muted pause-pending">Đang chờ tạm dừng…</small>}
      </td>
      <td className="mono" data-label="Bảng đích">
        {run.summary.target ?? "—"}
      </td>
      <td data-label="Tối ưu">
        {run.summary.optimization === "applied" ? `+${formatPct(run.summary.improvement_pct)}` : "—"}
      </td>
      <td className="num" data-label="Chi phí LLM">
        {run.summary.simulated ? "mô phỏng" : formatUsd(run.summary.cost_usd)}
      </td>
      <td className="muted small" data-label="Cập nhật">
        {formatTime(run.updated_at)}
      </td>
    </tr>
  );
}

// Lọc nhanh luôn hiện (thay lối tắt "Giám sát" của dock cũ); các bộ lọc khác vẫn mở được từ thẻ thống kê trang chủ.
const QUICK: { key: RunFilterKey | null; label: string }[] = [
  { key: null, label: "Tất cả" },
  { key: "dang-chay", label: "Đang chạy" },
  { key: "tam-dung", label: "Đã tạm dừng" },
  { key: "cho-toi", label: "Chờ tôi xử lý" },
  { key: "cua-toi", label: "Yêu cầu của tôi" },
];

function QuickFilters({ current }: { current: RunFilterKey | null }) {
  return (
    <nav className="quick-filters" aria-label="Lọc nhanh lần chạy">
      {QUICK.map(({ key, label }) => (
        <Link
          key={label}
          href={key ? runFilterHref(key) : "/runs"}
          className="quick-filter"
          aria-current={current === key ? "page" : undefined}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}

export function RunsTable() {
  const { runs: all, runsError: error, refreshRuns: refresh, user } = useApp();
  const key = useSearchParams().get("loc");
  const filter = isRunFilter(key) ? key : null;
  const data = all && filter ? filterRuns(all, filter, user) : all;
  const loading = !all && !error;
  const waiting = all?.filter((r) => NEEDS_ACTION.includes(r.status)).length ?? 0;
  return (
    <Card
      title="Lần chạy gần đây"
      actions={waiting > 0 && <span className="badge warn">{waiting} lần chạy cần bạn xử lý</span>}
    >
      <QuickFilters current={filter} />
      {filter && !QUICK.some((item) => item.key === filter) && (
        <p className="filter-bar">
          <span className="badge info">Đang lọc: {RUN_FILTERS[filter].label}</span>
          <Link href="/runs" className="small link-arrow">
            <Icon name="close" size={14} /> Bỏ lọc
          </Link>
        </p>
      )}
      {error && <ErrorBox message={error} onRetry={refresh} />}
      {loading && <Loading text="Đang tải danh sách lần chạy…" />}
      {data && data.length === 0 && (
        <Empty
          icon="runs"
          action={
            filter ? (
              <Link href="/runs" className="btn small">
                Bỏ lọc
              </Link>
            ) : (
              <Link href="/#request" className="btn primary small">
                <Icon name="create" size={16} /> Tạo yêu cầu mới
              </Link>
            )
          }
        >
          {filter
            ? "Không có lần chạy nào khớp bộ lọc."
            : "Chưa có lần chạy nào. Mô tả bằng lời bảng số liệu bạn cần, agent sẽ viết pipeline."}
        </Empty>
      )}
      {data && data.length > 0 && (
        <div className="table-wrap">
          <table className="stack-on-phone">
            <thead>
              <tr>
                <th>Yêu cầu</th>
                <th>Trạng thái</th>
                <th>Bảng đích</th>
                <th>Tối ưu</th>
                <th className="num">
                  Chi phí LLM <SampleTag />
                </th>
                <th>Cập nhật</th>
              </tr>
            </thead>
            <tbody>
              {data.map((run) => (
                <RunRow key={run.id} run={run} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
