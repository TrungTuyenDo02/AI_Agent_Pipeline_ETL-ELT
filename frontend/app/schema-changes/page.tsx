"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useApp } from "@/components/AppContext";
import { useToast } from "@/components/Toast";
import { Card, Empty, ErrorBox, Loading } from "@/components/ui";
import { apiPost, messageOf } from "@/lib/api";
import type { Accepted, DriftSeverity, SchemaChange } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

// Thay đổi cấu trúc nguồn (giai đoạn 5). Hệ thống chỉ phát hiện và báo: không tự tạo run, tự chạy hay tự merge. "Đề xuất bản vá"
// tạo một lần chạy MỚI đi qua luồng chuẩn (kiểm cấu trúc → sandbox → test → duyệt J2) và chỉ khi bạn bấm.

const SEVERITY: Record<DriftSeverity, { label: string; tone: string }> = {
  breaking: { label: "Chặn", tone: "danger" },
  warning: { label: "Cảnh báo", tone: "warn" },
  info: { label: "Thông tin", tone: "info" },
};
const STATUS = { open: "Đang mở", acknowledged: "Đã xác nhận", resolved: "Đã hết" } as const;

function ChangeRow({ change, canAct, onDone }: { change: SchemaChange; canAct: boolean; onDone: () => Promise<void> }) {
  const toast = useToast();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const open = change.status === "open";

  async function acknowledge() {
    setBusy(true);
    setError("");
    try {
      await apiPost(`/schema-changes/${change.id}/acknowledge`, {});
      toast("Đã dùng cấu trúc mới làm bản chuẩn.");
      await onDone();
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  }

  async function propose(runId: string) {
    setBusy(true);
    setError("");
    try {
      const accepted = await apiPost<Accepted>(`/runs/${runId}/patch`, {});
      toast("Đã tạo lần chạy bản vá.");
      router.push(`/runs/${accepted.run_id}`);
    } catch (exc) {
      setError(messageOf(exc));
      setBusy(false);
    }
  }

  const severity = SEVERITY[change.severity];
  return (
    <tr data-inactive={!open || undefined}>
      <td>
        <span className={`badge ${severity.tone}`}>{severity.label}</span>
      </td>
      <td>
        <strong>{change.source_name}</strong>
        <div className="mono small">{change.table}</div>
      </td>
      <td>
        {change.detail}
        {change.hint && <div className="muted small">{change.hint}</div>}
      </td>
      <td>
        {change.affected_pipelines?.length ? (
          <ul className="plain">
            {change.affected_pipelines.map((p) => (
              <li key={p.run_id}>
                <Link href={`/runs/${p.run_id}`} className="mono">
                  {p.run_id}
                </Link>
                {open && canAct && (
                  <button type="button" className="btn small" disabled={busy} onClick={() => propose(p.run_id)}>
                    Đề xuất bản vá
                  </button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <span className="muted">Chưa có pipeline nào dùng</span>
        )}
      </td>
      <td>
        {STATUS[change.status ?? "open"]}
        {change.acknowledged_by && <div className="muted small">bởi @{change.acknowledged_by}</div>}
      </td>
      <td>
        {open && canAct && (
          <button type="button" className="btn small" disabled={busy} onClick={acknowledge}>
            Tôi đã biết, dùng cấu trúc mới
          </button>
        )}
        {error && (
          <div className="small" style={{ color: "var(--fail)" }}>
            {error}
          </div>
        )}
      </td>
    </tr>
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

  return (
    <div className="stack">
      <header className="page-head">
        <h1>Thay đổi cấu trúc</h1>
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
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Mức</th>
                  <th>Nguồn / bảng</th>
                  <th>Thay đổi</th>
                  <th>Pipeline bị ảnh hưởng</th>
                  <th>Trạng thái</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.map((c) => (
                  <ChangeRow key={c.id} change={c} canAct={canAct} onDone={refresh} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
