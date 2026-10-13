"use client";

import { joinTouches } from "@/lib/diagram";
import { formatNumber, LAYER_LABELS } from "@/lib/format";
import type { IconName } from "@/lib/icons";
import type { CatalogView, ColumnInfo, TableInfo } from "@/lib/types";

import { Icon } from "../icons";
import { Card, Empty } from "../ui";

type TypeFamily = "num" | "text" | "time" | "bool" | "other";

/** Gom kiểu dữ liệu thành nhóm để tô màu nhãn kiểu (số / chữ / thời gian / đúng-sai). */
function typeFamily(type: string): TypeFamily {
  const t = type.toUpperCase();
  if (/INT|DEC|NUM|FLOAT|DOUBLE|REAL|HUGEINT/.test(t)) return "num";
  if (/CHAR|TEXT|STRING|UUID/.test(t)) return "text";
  if (/DATE|TIME|INTERVAL/.test(t)) return "time";
  if (/BOOL/.test(t)) return "bool";
  return "other";
}

function NullBar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="muted">—</span>;
  const tone = pct === 0 ? "ok" : pct < 10 ? "warn" : "danger";
  return (
    <span className="null-bar" data-tone={tone}>
      <span className="null-pct">{pct.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%</span>
      <span className="track" aria-hidden>
        <span className="fill" style={{ width: `${Math.min(pct, 100)}%` }} />
      </span>
    </span>
  );
}

function ColumnsTable({ columns }: { columns: ColumnInfo[] }) {
  return (
    <div className="table-wrap schema-cols-table">
      <table>
        <thead>
          <tr>
            <th>Cột</th>
            <th>Kiểu</th>
            <th className="num">% rỗng</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((column) => (
            <tr key={column.name}>
              <td>
                <span className="col-name">
                  {column.is_key ? (
                    <Icon name="keyColumn" size={14} weight="fill" className="col-key" aria-label="Cột khóa" />
                  ) : (
                    <span className="col-key-gap" aria-hidden />
                  )}
                  <span className="mono">{column.name}</span>
                </span>
              </td>
              <td>
                {column.type ? (
                  <span className={`type-chip t-${typeFamily(column.type)}`}>{column.type}</span>
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td className="num">
                <NullBar pct={column.null_pct} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Neighbours({ label, ids, onSelect }: { label: string; ids: string[]; onSelect: (id: string) => void }) {
  return (
    <div className="neighbours">
      <span className="neighbours-label">{label}</span>
      <span className="neighbours-list">
        {ids.length === 0 && <span className="muted">—</span>}
        {ids.map((id) => (
          <button key={id} type="button" className="chip mono" onClick={() => onSelect(id)}>
            {id}
          </button>
        ))}
      </span>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: IconName; label: string; value: string }) {
  return (
    <div className="schema-metric">
      <Icon name={icon} size={18} weight="duotone" />
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export function SchemaPanel({
  catalog,
  table,
  onSelect,
}: {
  catalog: CatalogView;
  table: TableInfo | undefined;
  onSelect: (id: string) => void;
}) {
  if (!table) {
    return (
      <Card title="Schema">
        <Empty>Bấm vào một bảng trên sơ đồ để xem cột, kiểu, % rỗng, khóa và quan hệ.</Empty>
      </Card>
    );
  }
  const upstream = catalog.lineage.filter((e) => e.target === table.id).map((e) => e.source);
  const downstream = catalog.lineage.filter((e) => e.source === table.id).map((e) => e.target);
  const joins = catalog.joins.filter((join) => joinTouches(join, table));
  const keyCount = table.columns.filter((column) => column.is_key).length;
  return (
    <Card
      title={
        <span className="schema-title">
          <Icon name="table" size={18} weight="duotone" />
          <span className="mono">{table.name}</span>
        </span>
      }
      actions={<span className="badge muted">{LAYER_LABELS[table.layer]}</span>}
    >
      <div className="schema-panel">
        {(table.description || table.group || table.file) && (
          <div className="schema-intro">
            {table.description && <p className="small">{table.description}</p>}
            <div className="row small muted">
              {table.group && <span className="badge info">{table.group}</span>}
              {table.file && <span className="mono">{table.file}</span>}
            </div>
          </div>
        )}
        <div className="schema-metrics">
          <Metric icon="columns" label="Cột" value={formatNumber(table.columns.length)} />
          <Metric icon="rows" label="Dòng" value={formatNumber(table.rows)} />
          <Metric icon="keyColumn" label="Cột khóa" value={formatNumber(keyCount)} />
        </div>
        {(table.duplicate_keys ?? 0) > 0 && (
          <div className="alert warn">
            <span className="alert-text">
              <Icon name="warning" size={16} weight="fill" />
              {formatNumber(table.duplicate_keys)} dòng trùng khóa — pipeline cần bỏ trùng hoặc làm rõ với nghiệp vụ.
            </span>
          </div>
        )}
        {catalog.lineage.length > 0 && (
          <section className="schema-section">
            <h3>Luồng dữ liệu</h3>
            <Neighbours label="Đọc từ" ids={upstream} onSelect={onSelect} />
            <Neighbours label="Được dùng bởi" ids={downstream} onSelect={onSelect} />
          </section>
        )}
        <section className="schema-section">
          <h3>Cấu trúc cột</h3>
          <ColumnsTable columns={table.columns} />
        </section>
        {joins.length > 0 && (
          <section className="schema-section">
            <h3>Khóa nối liên quan</h3>
            <ul className="join-list">
              {joins.map((join) => (
                <li key={`${join.left}-${join.right}-${join.model}`}>
                  <span className="mono join-cols">
                    {join.left} <Icon name="start" size={12} weight="bold" aria-hidden /> {join.right}
                  </span>
                  <span className="muted small">
                    {join.how}
                    {join.match_pct != null && ` · khớp ${join.match_pct}% dòng`}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </Card>
  );
}
