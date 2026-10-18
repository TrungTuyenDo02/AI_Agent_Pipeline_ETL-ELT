"use client";

import { useMemo, useState } from "react";

import type { RowReconciliation, RunFiles, SchemaReport, ValueFilter } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

import { CodeDiff, type LineHighlight } from "../CodeDiff";
import { ReviewGuide } from "../guide/Guide";
import { Card, Empty, ErrorBox, Loading } from "../ui";
import { DecisionForm } from "./DecisionForm";
import { EvidencePanel } from "./EvidencePanel";
import { CostFigures, OptimizationFigures } from "./ReviewFigures";
import { useRun } from "./RunContext";

interface FileGroup {
  title: string;
  paths: string[];
}

function groupFiles(files: RunFiles): FileGroup[] {
  const code = Object.keys(files.code_files).sort();
  return [
    { title: "Model dbt", paths: code.filter((p) => p.startsWith("models/")) },
    { title: "DAG Airflow", paths: code.filter((p) => p.startsWith("dags/")) },
    { title: "Khác", paths: code.filter((p) => !p.startsWith("models/") && !p.startsWith("dags/")) },
    { title: "Test (sinh mù code)", paths: Object.keys(files.test_files).sort() },
  ].filter((group) => group.paths.length > 0);
}

const PROPOSAL_LABELS: Record<string, string> = {
  added: "Cột mới",
  type_changed: "Đổi kiểu",
  new_values: "Giá trị mới",
  removed: "Cột bị xóa",
  rename: "Nghi đổi tên",
};

function highlightOf(filter: ValueFilter): LineHighlight {
  const where = filter.in_spec ? "" : " — giá trị KHÔNG có trong đặc tả/câu trả lời, có thể suy từ dữ liệu mẫu";
  return {
    line: filter.line,
    message: "Điều kiện cứng theo giá trị (" + filter.context + "): " + filter.expression + where,
  };
}

/** Mục 8–9: cấu trúc nguồn đổi (kèm đề xuất sửa), điều kiện cứng theo giá trị, số dòng vào → ra. Đo bằng code. */
function DataChecksCard({
  report,
  filters,
  reconciliation,
  decision,
}: {
  report?: SchemaReport | Record<string, never>;
  filters: ValueFilter[];
  reconciliation: RowReconciliation[];
  decision?: { by?: string; renames?: Record<string, string> };
}) {
  const changes = report && "changes" in report ? report.changes : [];
  const checked = report && "checked" in report ? report.checked : undefined;
  const note = report && "note" in report ? report.note : "";
  const proposals = changes.flatMap((c) => c.proposals.map((p) => ({ ...p, source: c.source })));
  const outside = filters.filter((f) => !f.in_spec).length;
  const renames = Object.entries(decision?.renames ?? {});
  return (
    <Card
      title="Kiểm tra dữ liệu (code đo)"
      actions={
        outside || proposals.length ? (
          <span className="badge warn">{outside + proposals.length} điểm cần xem</span>
        ) : (
          <span className="badge ok">Không có cảnh báo</span>
        )
      }
    >
      <div className="checks-grid">
        <section>
          <h3>Cấu trúc nguồn so với bản đã duyệt</h3>
          {checked === false && <p className="muted small">{note}</p>}
          {checked && proposals.length === 0 && <p className="small">Không đổi (hoặc nguồn lần đầu được duyệt).</p>}
          {decision?.by && (
            <p className="small">
              Engineer <strong>{decision.by}</strong> đã xác nhận chạy tiếp
              {renames.length > 0 ? "; đổi tên: " + renames.map(([a, b]) => a + " → " + b).join(", ") : ""}.
            </p>
          )}
          <ul className="check-list">
            {proposals.map((p, i) => (
              <li key={i}>
                <span className={p.kind === "removed" || p.kind === "rename" ? "badge danger" : "badge warn"}>
                  {PROPOSAL_LABELS[p.kind] ?? p.kind}
                </span>
                <div>
                  <span className="mono small">{p.source}</span> — {p.message}
                  {p.snippet && (
                    <div className="small">
                      Đề xuất{p.file ? " cho " + p.file : ""}: <code>{p.snippet}</code>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h3>Điều kiện cứng theo giá trị ({filters.length})</h3>
          {filters.length === 0 && <p className="small">Code không so sánh cột với giá trị cụ thể nào.</p>}
          <ul className="check-list">
            {filters.map((f, i) => (
              <li key={i}>
                <span className={f.in_spec ? "badge ok" : "badge warn"}>
                  {f.in_spec ? "có trong đặc tả" : "không có trong đặc tả"}
                </span>
                <div>
                  <code>{f.expression}</code>
                  <div className="small muted">
                    {f.file}:{f.line || "?"} · {f.context}
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {filters.length > 0 && (
            <p className="small muted">
              Các dòng này được tô vàng trong khung code. Giá trị hợp lệ phải do người dùng/đặc tả nêu.
            </p>
          )}
        </section>
        <section>
          <h3>Số dòng vào → ra (staging)</h3>
          {reconciliation.length === 0 && <p className="small muted">Chưa đo (lần chạy chưa qua V2).</p>}
          <ul className="check-list">
            {reconciliation.map((r) => {
              const diff = r.rows_in - r.rows_out;
              const label = diff === 0 ? "khớp" : diff > 0 ? "loại " + diff : "thêm " + -diff;
              return (
                <li key={r.model}>
                  <span className={diff === 0 ? "badge ok" : "badge warn"}>{label}</span>
                  <div>
                    <span className="mono">{r.source}</span> {r.rows_in} dòng → <span className="mono">{r.model}</span>{" "}
                    {r.rows_out} dòng
                    {diff !== 0 && (
                      <div className="small muted">
                        Cần lý do ghi rõ (khử trùng, lọc theo đặc tả) — không loại dòng im lặng.
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </Card>
  );
}

function FileList({
  files,
  selected,
  onSelect,
  flagged,
}: {
  files: RunFiles;
  selected: string;
  onSelect: (p: string) => void;
  flagged: Record<string, number>;
}) {
  const hasPrevious = Object.keys(files.previous_files).length > 0;
  const current = { ...files.code_files, ...files.test_files };
  return (
    <nav className="file-list" aria-label="Các file sinh ra">
      {groupFiles(files).map((group) => (
        <div key={group.title}>
          <h3>{group.title}</h3>
          {group.paths.map((path) => (
            <button
              key={path}
              type="button"
              className={path === selected ? "file-btn active" : "file-btn"}
              onClick={() => onSelect(path)}
              aria-current={path === selected}
            >
              <span>{path.split("/").pop()}</span>
              {flagged[path] > 0 && (
                <span className="badge warn" title="Có điều kiện cứng theo giá trị (tô vàng trong code)">
                  {flagged[path]} lọc cứng
                </span>
              )}
              {hasPrevious && files.previous_files[path] !== current[path] && (
                <span className="badge warn" title="Đổi so với vòng trước">
                  Đổi
                </span>
              )}
            </button>
          ))}
        </div>
      ))}
    </nav>
  );
}

function DiffCard({ files, filters }: { files: RunFiles; filters: ValueFilter[] }) {
  const all = { ...files.code_files, ...files.test_files };
  const paths = Object.keys(all);
  const [picked, setPicked] = useState("");
  const selected = paths.includes(picked)
    ? picked
    : (paths.find((p) => p.includes("/marts/") && p.endsWith(".sql")) ?? paths[0]);
  const hasPrevious = Object.keys(files.previous_files).length > 0;
  const flagged = useMemo(() => {
    const out: Record<string, number> = {};
    for (const f of filters) out[f.file] = (out[f.file] ?? 0) + 1;
    return out;
  }, [filters]);
  const highlights = useMemo(() => filters.filter((f) => f.file === selected).map(highlightOf), [filters, selected]);
  if (!selected) return <Empty>Agent chưa sinh code.</Empty>;
  return (
    <div className="review-layout">
      <FileList files={files} selected={selected} onSelect={setPicked} flagged={flagged} />
      <div className="stack" style={{ gap: 8 }}>
        <div className="row small muted">
          <span className="mono">{selected}</span>
          <span>·</span>
          <span>
            {hasPrevious ? "Trái: bản bạn từ chối ở vòng trước · Phải: bản mới" : "Vòng duyệt đầu: toàn bộ là code mới"}
          </span>
        </div>
        <CodeDiff
          path={selected}
          original={files.previous_files[selected] ?? ""}
          modified={all[selected]}
          highlights={highlights}
        />
      </div>
    </div>
  );
}

type ReviewTab = "code" | "optimize" | "cost";

const REVIEW_TABS: { id: ReviewTab; label: string }[] = [
  { id: "code", label: "Code sinh ra" },
  { id: "optimize", label: "Tối ưu" },
  { id: "cost", label: "Chi phí và thời gian" },
];

/** Màn duyệt: bằng chứng "Code đo | LLM nói" và nút quyết định lên đầu; code, tối ưu, chi phí đặt trong tab. */
export function ReviewScreen() {
  const { runId, detail } = useRun();
  const [tab, setTab] = useState<ReviewTab>("code");
  const version = detail?.record.updated_at ?? "";
  const files = usePoll<RunFiles>(detail ? `/runs/${runId}/files?v=${encodeURIComponent(version)}` : null, null);
  return (
    <>
      <ReviewGuide />
      <EvidencePanel />
      <div className="grid-2 review-top">
        <div className="decision">
          <DecisionForm />
        </div>
        {detail && (
          <DataChecksCard
            report={detail.schema_report}
            filters={detail.value_filters ?? []}
            reconciliation={detail.reconciliation ?? []}
            decision={detail.schema_decision}
          />
        )}
      </div>
      <div className="segmented" role="group" aria-label="Chi tiết để duyệt">
        {REVIEW_TABS.map((item) => (
          <button key={item.id} type="button" aria-pressed={tab === item.id} onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      {tab === "code" && (
        <Card title="Code sinh ra">
          {files.error && <ErrorBox message={files.error} onRetry={files.refresh} />}
          {!files.data && !files.error && <Loading text="Đang tải code…" />}
          {files.data && <DiffCard files={files.data} filters={detail?.value_filters ?? []} />}
        </Card>
      )}
      {tab === "optimize" && detail && <OptimizationFigures report={detail.optimization} />}
      {tab === "cost" && <CostFigures />}
    </>
  );
}
