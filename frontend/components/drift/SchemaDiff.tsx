"use client";

import { Loading, ErrorBox } from "@/components/ui";
import { CHANGE_LABELS } from "@/lib/drift";
import type { ChangeDiff, DiffRow } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

// Hình trước/sau của một thay đổi cấu trúc: bảng nào, cột nào, đổi gì. Chỉ tên cột và kiểu, không có dữ liệu.

const MARK: Record<DiffRow["status"], string> = {
  same: "",
  added: "+",
  removed: "−",
  changed: "~",
  renamed_from: "→",
  renamed_to: "←",
};

function Cell({ row, side }: { row: DiffRow; side: "before" | "after" }) {
  const present = side === "before" ? row.before_type : row.after_type;
  if (!present) return <div className="diff-cell empty" aria-hidden="true" />;
  const hot = row.status !== "same";
  return (
    <div className={`diff-cell ${hot ? row.status : ""}`}>
      <span className="diff-name">{row.name}</span>
      <span className="diff-type">{present}</span>
      {hot && (
        <span className="diff-mark" aria-hidden="true">
          {MARK[row.status]}
        </span>
      )}
    </div>
  );
}

export function SchemaDiffView({ diff }: { diff: ChangeDiff }) {
  if (diff.rows.length === 0) {
    return (
      <p className="muted small">
        {diff.change_type.startsWith("stat_")
          ? "Thay đổi về thống kê, không đổi cấu trúc cột."
          : "Không có ảnh chụp cấu trúc để so sánh."}
      </p>
    );
  }
  return (
    <div className="diff" role="table" aria-label={`So sánh cấu trúc bảng ${diff.table}`}>
      <div className="diff-head" role="row">
        <div role="columnheader">
          Trước <span className="muted">(phiên bản {diff.before_version})</span>
        </div>
        <div role="columnheader">
          Sau <span className="muted">(phiên bản {diff.after_version})</span>
        </div>
      </div>
      {diff.rows.map((row) => (
        <div className="diff-row" role="row" key={row.name} title={row.note || undefined}>
          <Cell row={row} side="before" />
          <Cell row={row} side="after" />
          {row.note && <div className="diff-note small muted">{row.note}</div>}
        </div>
      ))}
    </div>
  );
}

/** Tải hình so sánh của một thay đổi khi mở rộng thẻ. */
export function SchemaDiff({ changeId }: { changeId: number }) {
  const { data, error, loading } = usePoll<ChangeDiff>(`/schema-changes/${changeId}/diff`, null);
  if (loading && !data) return <Loading text="Đang vẽ so sánh…" lines={2} />;
  if (!data) return <ErrorBox message={error || "Không tải được so sánh."} />;
  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="small">
        <strong>{data.table}</strong> · {CHANGE_LABELS[data.change_type] ?? data.change_type}
        {data.column ? (
          <>
            {" "}
            · cột <span className="mono">{data.column}</span>
          </>
        ) : null}
      </div>
      <SchemaDiffView diff={data} />
    </div>
  );
}
