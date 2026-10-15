"use client";

import { useState, type FormEvent } from "react";

import { useApp } from "@/components/AppContext";
import { useToast } from "@/components/Toast";
import { Card, Empty, ErrorBox, Loading } from "@/components/ui";
import { apiPatch, apiPost, messageOf } from "@/lib/api";
import type { Department, GlossaryTerm } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

// Từ điển nghiệp vụ (giai đoạn 6): giúp AI hiểu đúng từ ngữ của công ty. Chỉ Admin thêm/sửa; AI chỉ đọc, không tự ghi.

const splitList = (text: string) =>
  text
    .split(/[,;\n]/)
    .map((s) => s.trim())
    .filter(Boolean);

function TermForm({
  departments,
  initial,
  onDone,
  onCancel,
}: {
  departments: Department[];
  initial?: GlossaryTerm;
  onDone: () => Promise<void>;
  onCancel?: () => void;
}) {
  const toast = useToast();
  const [term, setTerm] = useState(initial?.term ?? "");
  const [synonyms, setSynonyms] = useState(initial?.synonyms.join(", ") ?? "");
  const [definition, setDefinition] = useState(initial?.definition ?? "");
  const [mapsTo, setMapsTo] = useState(initial?.maps_to ?? "");
  const [departmentId, setDepartmentId] = useState<number>(initial?.department_id ?? 0);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError("");
    const body = {
      term,
      synonyms: splitList(synonyms),
      definition,
      maps_to: mapsTo,
      department_id: departmentId || (initial ? 0 : null),
    };
    try {
      if (initial) await apiPatch(`/glossary/${initial.id}`, body);
      else await apiPost("/glossary", body);
      toast(initial ? "Đã cập nhật thuật ngữ." : `Đã thêm thuật ngữ "${term}".`);
      if (!initial) {
        setTerm("");
        setSynonyms("");
        setDefinition("");
        setMapsTo("");
      }
      await onDone();
      onCancel?.();
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="stack" onSubmit={submit} style={{ gap: 8 }}>
      <div className="row" style={{ gap: 8 }}>
        <label className="field grow">
          <span>Thuật ngữ</span>
          <input value={term} onChange={(e) => setTerm(e.target.value)} maxLength={80} required />
        </label>
        <label className="field grow">
          <span>Từ đồng nghĩa (cách nhau bằng dấu phẩy)</span>
          <input value={synonyms} onChange={(e) => setSynonyms(e.target.value)} />
        </label>
        <label className="field">
          <span>Phạm vi</span>
          <select value={departmentId} onChange={(e) => setDepartmentId(Number(e.target.value))}>
            <option value={0}>Dùng chung mọi phòng ban</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="field">
        <span>Định nghĩa (ngắn, rõ, không ghi dữ liệu thật)</span>
        <textarea
          value={definition}
          onChange={(e) => setDefinition(e.target.value)}
          rows={2}
          maxLength={400}
          required
        />
      </label>
      <label className="field">
        <span>Ứng với bảng/cột hoặc biểu thức (tùy chọn)</span>
        <input value={mapsTo} onChange={(e) => setMapsTo(e.target.value)} maxLength={300} />
      </label>
      {error && <ErrorBox message={error} />}
      <div className="row" style={{ gap: 8 }}>
        <button type="submit" className="btn primary" disabled={sending || term.trim().length < 2}>
          {initial ? "Lưu thay đổi" : "Thêm thuật ngữ"}
        </button>
        {onCancel && (
          <button type="button" className="btn" onClick={onCancel}>
            Hủy
          </button>
        )}
      </div>
    </form>
  );
}

function TermRow({
  item,
  isAdmin,
  departments,
  scope,
  onDone,
}: {
  item: GlossaryTerm;
  isAdmin: boolean;
  departments: Department[];
  scope: string;
  onDone: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  if (editing) {
    return (
      <tr>
        <td colSpan={isAdmin ? 5 : 4}>
          <TermForm departments={departments} initial={item} onDone={onDone} onCancel={() => setEditing(false)} />
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td>
        <strong>{item.term}</strong>
        {item.synonyms.length > 0 && <div className="muted small">{item.synonyms.join(", ")}</div>}
      </td>
      <td>{item.definition}</td>
      <td className="mono small">{item.maps_to || "—"}</td>
      <td>{scope}</td>
      {isAdmin && (
        <td>
          <button type="button" className="btn small" onClick={() => setEditing(true)}>
            Sửa
          </button>
        </td>
      )}
    </tr>
  );
}

export function GlossaryPanel() {
  const { user } = useApp();
  const isAdmin = user?.role === "admin";
  const { data, error, loading, refresh } = usePoll<GlossaryTerm[]>("/glossary", null);
  const departments = usePoll<Department[]>(isAdmin ? "/departments" : null, null);
  const names = new Map((departments.data ?? []).map((d) => [d.id, d.name]));

  return (
    <div className="stack">
      {isAdmin && departments.data && (
        <Card title="Thêm thuật ngữ">
          <TermForm departments={departments.data} onDone={refresh} />
        </Card>
      )}
      <Card title="Từ điển nghiệp vụ">
        <p className="muted small">
          Khi yêu cầu của bạn dùng một thuật ngữ ở đây, AI nhận định nghĩa của nó (tối đa vài mục liên quan) để hiểu
          đúng ý công ty. Định nghĩa là chữ do quản trị viên viết; AI chỉ đọc, không tự thêm hay sửa.
        </p>
        {loading && !data ? (
          <Loading text="Đang tải từ điển…" />
        ) : !data ? (
          <ErrorBox message={error || "Không tải được từ điển."} onRetry={refresh} />
        ) : data.length === 0 ? (
          <Empty icon="sources">Chưa có thuật ngữ nào.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Thuật ngữ</th>
                  <th>Định nghĩa</th>
                  <th>Ứng với</th>
                  <th>Phạm vi</th>
                  {isAdmin && <th />}
                </tr>
              </thead>
              <tbody>
                {data.map((t) => (
                  <TermRow
                    key={t.id}
                    item={t}
                    isAdmin={isAdmin}
                    departments={departments.data ?? []}
                    scope={t.department_id ? (names.get(t.department_id) ?? `Phòng #${t.department_id}`) : "Dùng chung"}
                    onDone={refresh}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
