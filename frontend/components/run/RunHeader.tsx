"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { downloadUrl } from "@/lib/api";
import { formatTime } from "@/lib/format";

import { ErrorBox, Loading, StatusBadge } from "../ui";
import { PipelineTrack } from "./PipelineTrack";
import { useRun } from "./RunContext";

function Tabs({ runId }: { runId: string }) {
  const pathname = usePathname();
  const { detail } = useRun();
  const base = `/runs/${runId}`;
  const tabs = [
    { href: base, label: "Tổng quan" },
    { href: `${base}/review`, label: "Duyệt code", flag: detail?.record.status === "waiting_review" },
    { href: `${base}/optimize`, label: "Tối ưu" },
    { href: `${base}/catalog`, label: "Cấu trúc dữ liệu" },
  ];
  return (
    <nav className="tabs" aria-label="Các mục của lần chạy">
      {tabs.map((tab) => (
        <Link
          key={tab.href}
          href={tab.href}
          className={pathname === tab.href ? "tab active" : "tab"}
          aria-current={pathname === tab.href ? "page" : undefined}
        >
          {tab.label}
          {tab.flag && <span className="badge warn">chờ bạn</span>}
        </Link>
      ))}
    </nav>
  );
}

export function RunHeader() {
  const { runId, detail, error, loading, refresh } = useRun();
  if (loading && !detail) return <Loading text="Đang tải lần chạy…" />;
  if (!detail) return <ErrorBox message={error || "Không tải được lần chạy."} onRetry={refresh} />;
  const { record } = detail;
  const hasCode = record.status === "waiting_review" || record.status === "approved"; // đã có code chạy thử đạt
  return (
    <div className="run-head">
      <div className="run-title">
        <div>
          {/* mã lần chạy dài chỉ còn trong tooltip (CLAUDE.md yêu cầu 6) */}
          <Link href="/runs" className="small" title={`Mã lần chạy: ${record.id}`}>
            ← Lần chạy
          </Link>
          <h1>{record.request_text}</h1>
          <div className="row muted small run-meta">
            <span>{record.requester}</span>
            <span>·</span>
            <span>{formatTime(record.created_at)}</span>
            <span>·</span>
            {record.provider === "mock" ? (
              <span className="badge muted" title="LLM mô phỏng: câu trả lời cố định, chạy trong sandbox">
                Chạy thử (sandbox)
              </span>
            ) : (
              <span title={record.model}>LLM thật</span>
            )}
          </div>
        </div>
        <div className="run-actions">
          <StatusBadge status={record.status} />
          {detail.busy && <span className="badge info">agent đang chạy…</span>}
          {hasCode && (
            <a className="btn primary" href={downloadUrl(runId)} download>
              Tải gói code (.zip)
            </a>
          )}
        </div>
      </div>
      <PipelineTrack />
      {error && <ErrorBox message={`Mất kết nối, đang thử lại… (${error})`} />}
      <Tabs runId={runId} />
    </div>
  );
}
