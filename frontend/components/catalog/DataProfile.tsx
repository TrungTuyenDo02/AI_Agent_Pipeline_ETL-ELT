"use client";

// Hồ sơ dữ liệu kiểu Power Query / Tableau Prep (kiểu BA hay dùng): mỗi cột một thẻ có thanh chất lượng
// (hợp lệ / lỗi / rỗng) và biểu đồ phân bố, kèm kết luận nhanh, danh sách vấn đề và lưới dòng xem trước.
// Mọi con số do backend đo bằng code (0 token); dòng xem trước đã che email / số điện thoại.

import { useMemo, useState } from "react";

import { formatNumber, LAYER_LABELS } from "@/lib/format";
import type { CatalogView, ColumnKind, ColumnProfile, ProfileIssue, TableInfo, TableProfile } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

import { Checkbox, Empty, ErrorBox, Loading } from "../ui";

const KIND_GLYPH: Record<ColumnKind, string> = { number: "123", date: "Ngày", text: "Abc", bool: "T/F", nested: "{ }" };
const KIND_LABEL: Record<ColumnKind, string> = {
  number: "Số",
  date: "Ngày giờ",
  text: "Chữ",
  bool: "Đúng/sai",
  nested: "Lồng nhau",
};
const DATASET_LABELS: Record<string, string> = {
  sandbox: "Dữ liệu nguồn",
  small: "Mẫu nhỏ",
  dirty: "Dữ liệu bẩn",
  dupkeys: "Trùng khóa",
  nullmoney: "Tiền rỗng",
  few: "3 dòng",
  empty: "Bảng rỗng",
};
const DATASET_HINTS: Record<string, string> = {
  sandbox: "Dữ liệu nguồn đã nạp vào sandbox của lần chạy",
  small: "Mẫu ngẫu nhiên nhỏ (sinh bằng code, seed cố định)",
  dirty: "Cột phân loại bị làm bẩn có chủ đích: viết hoa, thừa khoảng trắng, rỗng, giá trị lạ; tiền rỗng",
  dupkeys: "Một số dòng bị trùng khóa có chủ đích",
  nullmoney: "Mọi cột tiền rỗng",
  few: "Chỉ 3 dòng",
  empty: "Không có dòng nào",
};
const LEVEL_LABEL = { fail: "Lỗi", warn: "Cần xem", info: "Lưu ý" } as const;
const LEVEL_TONE = { fail: "danger", warn: "warn", info: "info" } as const;

const pct = (part: number, whole: number) => (whole ? (100 * part) / whole : 0);
const fmtPct = (value: number) => `${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;

interface Quality {
  valid: number;
  invalid: number;
  blank: number;
  nulls: number;
}

function quality(column: ColumnProfile): Quality {
  return {
    valid: Math.max(column.filled - column.invalid - column.blank, 0),
    invalid: column.invalid,
    blank: column.blank,
    nulls: column.nulls,
  };
}

/** Hiện khoảng trắng thừa và chuỗi rỗng — đúng thứ BA cần thấy khi soi dữ liệu bẩn. */
function ShownValue({ value }: { value: string | null }) {
  if (value === null) return <span className="cell-null">null</span>;
  if (value.trim() === "") return <span className="cell-blank">(trống)</span>;
  if (value !== value.trim()) {
    const lead = value.length - value.trimStart().length;
    const trail = value.length - value.trimEnd().length;
    return (
      <span title="Có khoảng trắng thừa">
        <span className="cell-space">{"␣".repeat(lead)}</span>
        {value.trim()}
        <span className="cell-space">{"␣".repeat(trail)}</span>
      </span>
    );
  }
  return <>{value}</>;
}

function QualityBar({ q, total, thin = false }: { q: Quality; total: number; thin?: boolean }) {
  const parts: [keyof Quality, string][] = [
    ["valid", "Hợp lệ"],
    ["invalid", "Không đọc được"],
    ["blank", "Chuỗi rỗng"],
    ["nulls", "NULL"],
  ];
  const title = parts.map(([k, label]) => `${label}: ${formatNumber(q[k])} (${fmtPct(pct(q[k], total))})`).join("\n");
  return (
    <div className={`qbar${thin ? " thin" : ""}`} title={title} role="img" aria-label={title}>
      {parts.map(([k]) => q[k] > 0 && <span key={k} className={`q-${k}`} style={{ flexGrow: q[k] }} />)}
    </div>
  );
}

function TopValues({ column }: { column: ColumnProfile }) {
  const max = Math.max(...column.top.map((v) => v.count), 1);
  return (
    <ul className="dist-top">
      {column.top.map((v) => (
        <li key={v.label}>
          <span className="dist-label mono" title={v.label}>
            <ShownValue value={v.label} />
          </span>
          <span className="dist-track">
            <span style={{ width: `${pct(v.count, max)}%` }} />
          </span>
          <span className="dist-count">{formatNumber(v.count)}</span>
        </li>
      ))}
      {column.other > 0 && <li className="muted small dist-other">+ {formatNumber(column.other)} dòng giá trị khác</li>}
    </ul>
  );
}

function Histogram({ column }: { column: ColumnProfile }) {
  const max = Math.max(...column.bins.map((b) => b.count), 1);
  return (
    <div>
      <div className="dist-hist" role="img" aria-label={`Phân bố ${column.name}`}>
        {column.bins.map((b) => (
          <span key={b.label} title={`từ ${b.label}: ${formatNumber(b.count)} dòng`}>
            <span style={{ height: `${Math.max(pct(b.count, max), b.count ? 4 : 0)}%` }} />
          </span>
        ))}
      </div>
      <div className="dist-axis mono">
        <span>{column.minimum}</span>
        <span>{column.maximum}</span>
      </div>
    </div>
  );
}

function Distribution({ column }: { column: ColumnProfile }) {
  if (column.filled === 0) return <p className="muted small dist-note">Không có giá trị.</p>;
  // Cột mã số (id, khóa): biểu đồ khoảng gần như phẳng, không nói lên gì → ghi chú "dạng mã" thay vì vẽ
  const idLike = column.is_key || /(^id$|_(id|no|code)$)/i.test(column.name);
  if (column.bins.length > 0 && !(column.near_unique && idLike)) return <Histogram column={column} />;
  if (column.near_unique) {
    return (
      <p className="muted small dist-note">
        Gần như mỗi dòng một giá trị ({formatNumber(column.distinct)} khác nhau) — dạng mã / định danh.
      </p>
    );
  }
  return <TopValues column={column} />;
}

function ColumnCard({
  column,
  rows,
  issues,
  active,
  onPick,
}: {
  column: ColumnProfile;
  rows: number;
  issues: ProfileIssue[];
  active: boolean;
  onPick: () => void;
}) {
  const q = quality(column);
  const worst = issues.find((i) => i.level === "fail") ?? issues.find((i) => i.level === "warn") ?? issues[0];
  return (
    <article
      id={`col-${column.name}`}
      className={`col-card${active ? " active" : ""}`}
      data-level={worst?.level ?? "ok"}
      onClick={onPick}
    >
      <header>
        <span className={`kind kind-${column.kind}`} title={`${KIND_LABEL[column.kind]} · ${column.type}`}>
          {KIND_GLYPH[column.kind]}
        </span>
        <strong className="mono" title={column.name}>
          {column.name}
        </strong>
        {column.is_key && <span className="badge info">khóa</span>}
      </header>
      <QualityBar q={q} total={rows} />
      <div className="q-legend small">
        <span className="q-valid-text">{fmtPct(pct(q.valid, rows))} hợp lệ</span>
        {q.invalid > 0 && <span className="q-invalid-text">{formatNumber(q.invalid)} lỗi</span>}
        {q.blank + q.nulls > 0 && <span className="muted">{fmtPct(pct(q.blank + q.nulls, rows))} rỗng</span>}
      </div>
      <Distribution column={column} />
      <footer className="small muted">
        <span>{formatNumber(column.distinct)} khác nhau</span>
        {column.mean !== null && <span>TB {column.mean.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}</span>}
        {issues.length > 0 && (
          <span className={`badge ${LEVEL_TONE[worst.level]}`}>
            {issues.length} {LEVEL_LABEL[worst.level].toLowerCase()}
          </span>
        )}
      </footer>
    </article>
  );
}

function Verdict({ profile }: { profile: TableProfile }) {
  const fails = profile.issues.filter((i) => i.level === "fail").length;
  const warns = profile.issues.filter((i) => i.level === "warn").length;
  if (fails > 0) {
    return (
      <div className="verdict danger">
        <strong>Chưa ổn</strong>
        <span>
          {fails} lỗi phải xử lý trước khi dùng bảng này{warns > 0 && `, thêm ${warns} điểm cần xem`}.
        </span>
      </div>
    );
  }
  if (warns > 0) {
    return (
      <div className="verdict warn">
        <strong>Dùng được, cần xem lại</strong>
        <span>{warns} điểm cần xem — pipeline phải xử lý hoặc ghi rõ lý do.</span>
      </div>
    );
  }
  return (
    <div className="verdict ok">
      <strong>Ổn theo các luật kiểm</strong>
      <span>Không thấy cột rỗng bất thường, giá trị không đọc được, trùng khóa hay lệch số dòng.</span>
    </div>
  );
}

function Kpis({ profile }: { profile: TableProfile }) {
  const cells = profile.rows * profile.columns.length;
  const totals = profile.columns.map(quality).reduce(
    (acc, q) => ({
      valid: acc.valid + q.valid,
      invalid: acc.invalid + q.invalid,
      empty: acc.empty + q.blank + q.nulls,
    }),
    { valid: 0, invalid: 0, empty: 0 },
  );
  const bad = new Set(profile.issues.filter((i) => i.level !== "info" && i.column).map((i) => i.column)).size;
  const rowsHint =
    profile.rows_in !== null ? `vào ${formatNumber(profile.rows_in)} → ra ${formatNumber(profile.rows)}` : "";
  return (
    <div className="kpis">
      <div className="kpi">
        <span>Số dòng</span>
        <strong>{formatNumber(profile.rows)}</strong>
        {rowsHint && (
          <em className={profile.rows_in === profile.rows ? "ok" : "warn"} title="Đối chiếu số dòng (mục 9)">
            {rowsHint}
          </em>
        )}
      </div>
      <div className="kpi">
        <span>Số cột</span>
        <strong>{profile.columns.length}</strong>
        <em>{bad > 0 ? `${bad} cột cần xem` : "không cột nào lỗi"}</em>
      </div>
      <div className="kpi">
        <span>Ô hợp lệ</span>
        <strong>{fmtPct(pct(totals.valid, cells))}</strong>
        <em>
          {formatNumber(totals.invalid)} không đọc được · {fmtPct(pct(totals.empty, cells))} rỗng
        </em>
      </div>
      <div className="kpi">
        <span>Trùng khóa</span>
        <strong>{profile.keys.length ? formatNumber(profile.duplicate_keys ?? 0) : "—"}</strong>
        <em className="mono">{profile.keys.length ? profile.keys.join(", ") : "chưa xác định khóa"}</em>
      </div>
    </div>
  );
}

function Issues({ issues, onPick }: { issues: ProfileIssue[]; onPick: (column: string) => void }) {
  if (issues.length === 0) return null;
  const order = { fail: 0, warn: 1, info: 2 };
  const sorted = [...issues].sort((a, b) => order[a.level] - order[b.level]);
  return (
    <ul className="issue-list">
      {sorted.map((issue, i) => (
        <li key={`${issue.column}-${i}`}>
          <span className={`badge ${LEVEL_TONE[issue.level]}`}>{LEVEL_LABEL[issue.level]}</span>
          {issue.column ? (
            <button type="button" className="chip mono" onClick={() => onPick(issue.column)}>
              {issue.column}
            </button>
          ) : (
            <span className="chip muted">cả bảng</span>
          )}
          <span>{issue.text}</span>
        </li>
      ))}
    </ul>
  );
}

function PreviewGrid({ profile, columns, active }: { profile: TableProfile; columns: number[]; active: string }) {
  if (profile.preview.length === 0) return <Empty>Bảng không có dòng nào.</Empty>;
  return (
    <div className="table-wrap preview-grid">
      <table>
        <thead>
          <tr>
            <th className="num">#</th>
            {columns.map((i) => {
              const column = profile.columns[i];
              return (
                <th key={column.name} className={column.name === active ? "active" : undefined}>
                  <span className="th-name">
                    <span className={`kind kind-${column.kind}`}>{KIND_GLYPH[column.kind]}</span>
                    <span className="mono">{column.name}</span>
                  </span>
                  <QualityBar q={quality(column)} total={profile.rows} thin />
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {profile.preview.map((row, r) => (
            <tr key={r}>
              <td className="num muted">{r + 1}</td>
              {columns.map((i) => (
                <td
                  key={profile.columns[i].name}
                  className={`${profile.columns[i].kind === "number" ? "num " : ""}${profile.columns[i].name === active ? "active" : ""}`}
                >
                  <ShownValue value={row[i]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProfileBody({ profile }: { profile: TableProfile }) {
  const [active, setActive] = useState("");
  const [onlyIssues, setOnlyIssues] = useState(false);
  const byColumn = useMemo(() => {
    const map = new Map<string, ProfileIssue[]>();
    profile.issues.forEach((i) => i.column && map.set(i.column, [...(map.get(i.column) ?? []), i]));
    return map;
  }, [profile]);
  const shown = profile.columns
    .map((column, i) => ({ column, i }))
    .filter(({ column }) => !onlyIssues || byColumn.has(column.name));
  const pick = (name: string) => {
    setActive(name);
    document.getElementById(`col-${name}`)?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  };
  return (
    <>
      <Verdict profile={profile} />
      <Kpis profile={profile} />
      <Issues issues={profile.issues} onPick={pick} />
      <div className="profile-section-head">
        <h3>Hồ sơ từng cột</h3>
        <div className="row small">
          <span className="legend-q">
            <i className="q-valid" /> hợp lệ <i className="q-invalid" /> không đọc được <i className="q-blank" /> chuỗi
            rỗng <i className="q-nulls" /> NULL
          </span>
          {byColumn.size > 0 && (
            <Checkbox checked={onlyIssues} onChange={setOnlyIssues}>
              Chỉ cột có vấn đề
            </Checkbox>
          )}
        </div>
      </div>
      <div className="col-strip">
        {shown.map(({ column }) => (
          <ColumnCard
            key={column.name}
            column={column}
            rows={profile.rows}
            issues={byColumn.get(column.name) ?? []}
            active={column.name === active}
            onPick={() => setActive(column.name === active ? "" : column.name)}
          />
        ))}
      </div>
      <div className="profile-section-head">
        <h3>Xem trước {formatNumber(profile.preview.length)} dòng đầu</h3>
        <span className="small muted">Email, số điện thoại đã được che · ␣ = khoảng trắng thừa</span>
      </div>
      <PreviewGrid profile={profile} columns={shown.map(({ i }) => i)} active={active} />
    </>
  );
}

function TableList({
  tables,
  selected,
  onSelect,
  aiLayers,
}: {
  tables: TableInfo[];
  selected: string;
  onSelect: (id: string) => void;
  aiLayers: boolean;
}) {
  const groups = useMemo(() => {
    const out = new Map<string, TableInfo[]>();
    const order = aiLayers ? ["mart", "staging", "source"] : [];
    const label = (t: TableInfo) =>
      aiLayers ? (t.layer === "source" ? "Nguồn (raw)" : `${LAYER_LABELS[t.layer]} · code AI sinh`) : t.group || "Khác";
    [...tables]
      .sort((a, b) => order.indexOf(a.layer) - order.indexOf(b.layer))
      .forEach((t) => out.set(label(t), [...(out.get(label(t)) ?? []), t]));
    return [...out.entries()];
  }, [tables, aiLayers]);
  return (
    <nav className="table-list" aria-label="Chọn bảng">
      {groups.map(([group, items]) => (
        <div key={group}>
          <h4>{group}</h4>
          {items.map((t) => (
            <button
              key={t.id}
              type="button"
              aria-pressed={t.id === selected}
              data-layer={t.layer}
              onClick={() => onSelect(t.id)}
            >
              <span className="mono">{t.name}</span>
              <span className="small muted">
                {t.rows !== null ? `${formatNumber(t.rows)} dòng · ` : ""}
                {t.columns.length} cột
              </span>
            </button>
          ))}
        </div>
      ))}
    </nav>
  );
}

function profilePath(base: string, table: TableInfo, dataset: string): string {
  if (base === "/catalog/sources") return `/catalog/sources/profile?table=${encodeURIComponent(table.name)}`;
  return `${base.replace(/\/catalog$/, "/profile")}?table=${encodeURIComponent(table.id)}&dataset=${dataset}`;
}

export function DataProfile({ catalog, base, initial }: { catalog: CatalogView; base: string; initial: string }) {
  const runScoped = base !== "/catalog/sources";
  const [selected, setSelected] = useState(initial || catalog.tables[0]?.id || "");
  const [dataset, setDataset] = useState("sandbox");
  const table = catalog.tables.find((t) => t.id === selected);
  const { data, error, refresh } = usePoll<TableProfile>(table ? profilePath(base, table, dataset) : null, null);
  const current = data && data.id === table?.id && (!runScoped || data.dataset === dataset) ? data : null;
  return (
    <div className="profile-layout">
      <TableList tables={catalog.tables} selected={selected} onSelect={setSelected} aiLayers={runScoped} />
      <section className="card profile-card">
        {table && (
          <header className="profile-head">
            <div>
              <h2 className="mono">{table.name}</h2>
              <div className="row small muted">
                <span className="badge muted">{LAYER_LABELS[table.layer]}</span>
                {table.layer !== "source" && <span className="badge ai">Code AI sinh</span>}
                {table.group && <span className="badge info">{table.group}</span>}
                {table.file && <span className="mono">{table.file}</span>}
              </div>
              {table.description && <p className="small muted">{table.description}</p>}
            </div>
            {runScoped && current && current.datasets.length > 1 && (
              <div className="dataset-pick" role="group" aria-label="Chạy trên bộ dữ liệu">
                <span className="small muted">Chạy trên</span>
                <div className="segmented">
                  {current.datasets.map((name) => (
                    <button
                      key={name}
                      type="button"
                      aria-pressed={name === dataset}
                      title={DATASET_HINTS[name]}
                      onClick={() => setDataset(name)}
                    >
                      {DATASET_LABELS[name] ?? name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </header>
        )}
        <div className="profile-body">
          {!table && <Empty>Chọn một bảng ở cột bên trái.</Empty>}
          {table && !current && !error && <Loading text="Đang đo hồ sơ dữ liệu (DuckDB, 0 token)…" />}
          {table && !current && error && <ErrorBox message={error} onRetry={refresh} />}
          {current && <ProfileBody key={`${current.id}-${current.dataset}`} profile={current} />}
        </div>
      </section>
    </div>
  );
}
