"use client";

import Link from "next/link";
import { useState } from "react";

import { useApp } from "@/components/AppContext";
import { AdvicePanel } from "@/components/drift/AdvicePanel";
import { PatchPanel } from "@/components/drift/PatchPanel";
import { SchemaDiff } from "@/components/drift/SchemaDiff";
import { useToast } from "@/components/Toast";
import { Card, Empty, ErrorBox, Loading } from "@/components/ui";
import { apiPost, messageOf } from "@/lib/api";
import { CHANGE_LABELS, SEVERITY_LABELS } from "@/lib/drift";
import type { SchemaChange } from "@/lib/types";
import { notifyDriftChanged } from "@/lib/useDriftAlerts";
import { usePoll } from "@/lib/usePoll";

// Thay đổi cấu trúc nguồn (giai đoạn 5). Hệ thống chỉ phát hiện và báo: không tự tạo run, tự chạy hay tự merge. "Đề xuất bản vá"
// tạo một lần chạy MỚI đi qua luồng chuẩn (kiểm cấu trúc → sandbox → test → duyệt J2) và chỉ khi bạn bấm.

const STATUS = { open: "Đang mở", acknowledged: "Đã xác nhận", resolved: "Đã hết" } as const;

function ChangeCard({
  change,
  canAct,
  onDone,
}: {
  change: SchemaChange;
  canAct: boolean;
  onDone: () => Promise<void>;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [patching, setPatching] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [showDiff, setShowDiff] = useState(change.severity === "breaking" && change.status === "open");
  const open = change.status === "open";
  const severity = SEVERITY_LABELS[change.severity];
  const pipelines = change.affected_pipelines ?? [];

  async function acknowledge() {
    setBusy(true);
    setError("");
    try {
      await apiPost(`/schema-changes/${change.id}/acknowledge`, {});
      toast("Đã dùng cấu trúc mới làm bản chuẩn.");
      notifyDriftChanged();
      await onDone();
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className={`drift-card ${change.severity}`} data-inactive={!open || undefined}>
      <header className="drift-card-head">
        <span className={`badge ${severity.tone}`}>{severity.label}</span>
        <strong>{CHANGE_LABELS[change.change_type] ?? change.change_type}</strong>
        <span className="muted small">
          {change.source_name} · <span className="mono">{change.table}</span>
        </span>
        <span className="drift-status small muted">
          {STATUS[change.status ?? "open"]}
          {change.acknowledged_by ? ` · @${change.acknowledged_by}` : ""}
        </span>
      </header>
      <p>{change.detail}</p>
      {change.hint && <p className="muted small">{change.hint}</p>}

      <button type="button" className="btn small" aria-expanded={showDiff} onClick={() => setShowDiff(!showDiff)}>
        {showDiff ? "Ẩn so sánh trước/sau" : "Xem so sánh trước/sau"}
      </button>
      {showDiff && <SchemaDiff changeId={change.id} />}

      <div className="drift-pipelines">
        {pipelines.length ? (
          <ul className="plain">
            {pipelines.map((p) => (
              <li key={p.run_id} className="stack" style={{ gap: 6 }}>
                <div className="row" style={{ gap: 8, alignItems: "center" }}>
                  <span className="muted small">Pipeline bị ảnh hưởng:</span>
                  <Link href={`/runs/${p.run_id}`} className="mono">
                    {p.run_id}
                  </Link>
                  {open && canAct && (
                    <button
                      type="button"
                      className="btn small"
                      aria-expanded={patching === p.run_id}
                      onClick={() => setPatching(patching === p.run_id ? null : p.run_id)}
                    >
                      Đề xuất bản vá
                    </button>
                  )}
                </div>
                {patching === p.run_id && <PatchPanel runId={p.run_id} onClose={() => setPatching(null)} />}
                {canAct && <AdvicePanel changeId={change.id} runId={p.run_id} />}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted small">Chưa có pipeline đã sinh nào dùng bảng/cột này.</p>
        )}
      </div>

      {open && canAct && (
        <div className="row" style={{ gap: 8 }}>
          <button type="button" className="btn" disabled={busy} onClick={acknowledge}>
            Tôi đã biết, dùng cấu trúc mới
          </button>
        </div>
      )}
      {error && <ErrorBox message={error} />}
    </article>
  );
}

export default function SchemaChangesPage() {
  const { user } = useApp();
  const canAct = user?.role === "admin" || user?.role === "engineer";
  const [only, setOnly] = useState<"open" | "all">("open");
  const { data, error, loading, refresh } = usePoll<SchemaChange[]>(
    `/schema-changes${only === "open" ? "?status=open" : ""}`,
    null,
  );
  const breaking = (data ?? []).filter((c) => c.severity === "breaking" && c.status === "open").length;

  return (
    <div className="stack">
      <header className="page-head">
        <h1>
          Thay đổi cấu trúc
          {breaking > 0 && (
            <span className="count-oval" role="status" aria-label={`${breaking} thay đổi chặn đang mở`}>
              {breaking}
            </span>
          )}
        </h1>
        <p className="muted">
          Phát hiện khi nguồn đổi kiểu, đổi tên hoặc xóa cột, và chỉ ra pipeline bị ảnh hưởng. Hệ thống không ngăn được
          việc đổi và không tự sửa. Thay đổi mức &quot;Chặn&quot; dừng lần chạy mới cho tới khi bạn xác nhận.
        </p>
      </header>
      <Card
        title="Thay đổi đã phát hiện"
        actions={
          <div className="segmented" role="group" aria-label="Lọc">
            <button type="button" aria-pressed={only === "open"} onClick={() => setOnly("open")}>
              Đang mở
            </button>
            <button type="button" aria-pressed={only === "all"} onClick={() => setOnly("all")}>
              Tất cả
            </button>
          </div>
        }
      >
        {loading && !data ? (
          <Loading text="Đang tải thay đổi cấu trúc…" />
        ) : !data ? (
          <ErrorBox message={error || "Không tải được danh sách."} onRetry={refresh} />
        ) : data.length === 0 ? (
          <Empty icon="sources">Chưa có thay đổi cấu trúc nào{only === "open" ? " đang mở" : ""}.</Empty>
        ) : (
          <div className="stack" style={{ gap: 12 }}>
            {data.map((c) => (
              <ChangeCard key={c.id} change={c} canAct={canAct} onDone={refresh} />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
