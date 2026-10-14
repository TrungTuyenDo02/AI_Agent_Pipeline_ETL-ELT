"use client";

import { useState, type FormEvent } from "react";

import { useApp } from "@/components/AppContext";
import { useToast } from "@/components/Toast";
import { Card, Empty, ErrorBox, Loading } from "@/components/ui";
import { apiPatch, apiPost, messageOf } from "@/lib/api";
import type { Department, DriftReport, LLMAccess, Sensitivity, SourceKind, SourceView } from "@/lib/types";
import { usePoll } from "@/lib/usePoll";

// Sổ nguồn dữ liệu (CLAUDE.md bản 2, giai đoạn 3). Người thường chỉ thấy nguồn của phòng ban mình; Admin đăng ký, sửa nguồn.
// Mọi giới hạn (trần mức truy cập theo độ nhạy cảm) do backend kiểm; form chỉ gợi ý để khỏi chọn nhầm.

const KINDS: Record<SourceKind, string> = {
  file: "Tệp (CSV/JSON/SQLite)",
  duckdb: "DuckDB",
  postgres: "PostgreSQL (chỉ đọc)",
};
const SENSITIVITY: Record<Sensitivity, string> = { low: "Thấp", medium: "Trung bình", high: "Cao" };
const ACCESS: Record<LLMAccess, string> = {
  schema_only: "AI chỉ thấy cấu trúc",
  profile: "AI thấy thống kê, không thấy dòng thật",
  masked_sample: "AI thấy vài dòng đã che",
};
const ACCESS_ORDER: LLMAccess[] = ["schema_only", "profile", "masked_sample"];
const MAX_ACCESS: Record<Sensitivity, LLMAccess> = { high: "schema_only", medium: "profile", low: "masked_sample" };

function allowedAccess(sensitivity: Sensitivity): LLMAccess[] {
  return ACCESS_ORDER.slice(0, ACCESS_ORDER.indexOf(MAX_ACCESS[sensitivity]) + 1);
}

function RegisterForm({ departments, onDone }: { departments: Department[]; onDone: () => Promise<void> }) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [departmentId, setDepartmentId] = useState<number | "">(departments[0]?.id ?? "");
  const [kind, setKind] = useState<SourceKind>("file");
  const [secretRef, setSecretRef] = useState("");
  const [tables, setTables] = useState("*");
  const [sensitivity, setSensitivity] = useState<Sensitivity>("medium");
  const [access, setAccess] = useState<LLMAccess>("profile");
  const [restricted, setRestricted] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const options = allowedAccess(sensitivity);

  function chooseSensitivity(value: Sensitivity) {
    setSensitivity(value);
    if (!allowedAccess(value).includes(access)) setAccess(MAX_ACCESS[value]); // hạ về trần cho phép
  }

  const list = (text: string) =>
    text
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError("");
    try {
      await apiPost("/sources", {
        name,
        department_id: departmentId,
        kind,
        secret_ref: kind === "file" ? "" : secretRef,
        allowed_tables: list(tables),
        sensitivity,
        llm_access: access,
        restricted_columns: list(restricted),
      });
      toast(`Đã đăng ký nguồn "${name}".`);
      setName("");
      setSecretRef("");
      await onDone();
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setSending(false);
    }
  }

  return (
    <Card title="Đăng ký nguồn mới">
      <form className="admin-form" onSubmit={submit}>
        <label>
          <span>Tên nguồn</span>
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required />
        </label>
        <label>
          <span>Phòng ban</span>
          <select value={departmentId} onChange={(e) => setDepartmentId(Number(e.target.value))} required>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Loại nguồn</span>
          <select value={kind} onChange={(e) => setKind(e.target.value as SourceKind)}>
            {(Object.keys(KINDS) as SourceKind[]).map((k) => (
              <option key={k} value={k}>
                {KINDS[k]}
              </option>
            ))}
          </select>
        </label>
        {kind !== "file" && (
          <label>
            <span>Tên tham chiếu bí mật (không phải mật khẩu)</span>
            <input
              className="mono"
              value={secretRef}
              onChange={(e) => setSecretRef(e.target.value)}
              placeholder="vd: conn_orders_db"
              maxLength={64}
              autoComplete="off"
              required
            />
          </label>
        )}
        <label>
          <span>Bảng được phép (cách nhau bằng dấu phẩy, * = mọi bảng)</span>
          <input className="mono" value={tables} onChange={(e) => setTables(e.target.value)} required />
        </label>
        <label>
          <span>Độ nhạy cảm</span>
          <select value={sensitivity} onChange={(e) => chooseSensitivity(e.target.value as Sensitivity)}>
            {(Object.keys(SENSITIVITY) as Sensitivity[]).map((s) => (
              <option key={s} value={s}>
                {SENSITIVITY[s]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>AI được thấy gì</span>
          <select value={access} onChange={(e) => setAccess(e.target.value as LLMAccess)}>
            {options.map((a) => (
              <option key={a} value={a}>
                {ACCESS[a]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Cột nhạy cảm đánh dấu thêm (cách nhau bằng dấu phẩy)</span>
          <input className="mono" value={restricted} onChange={(e) => setRestricted(e.target.value)} />
        </label>
        <div className="admin-form-actions">
          <button type="submit" className="btn primary" disabled={sending || !name.trim() || !departmentId}>
            {sending ? "Đang đăng ký…" : "Đăng ký nguồn"}
          </button>
        </div>
      </form>
      <small className="muted">
        Nguồn độ nhạy cảm Cao chỉ cho AI xem cấu trúc; Trung bình tối đa thống kê; chỉ nguồn Thấp mới cho AI xem vài
        dòng đã che. Mật khẩu và chuỗi kết nối đặt trên máy chủ, không nhập ở đây.
      </small>
      {error && <ErrorBox message={error} />}
    </Card>
  );
}

function SourceRow({ source, isAdmin, onDone }: { source: SourceView; isAdmin: boolean; onDone: () => Promise<void> }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function update(body: Partial<{ llm_access: LLMAccess; enabled: boolean }>) {
    setBusy(true);
    setError("");
    try {
      await apiPatch(`/sources/${source.id}`, body);
      toast(`Đã cập nhật nguồn "${source.name}".`);
      await onDone();
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  }

  const { user } = useApp();
  const canCheck = user?.role === "admin" || user?.role === "engineer";

  async function checkDrift() {
    setBusy(true);
    setError("");
    try {
      const report = await apiPost<DriftReport>(`/sources/${source.id}/check-drift`, {});
      const blocking = report.open_breaking.length;
      toast(
        report.unreachable.length
          ? "Không kiểm được nguồn này (mất kết nối hoặc thiếu bí mật)."
          : blocking
            ? `Có ${blocking} thay đổi chặn đang mở: xem trang Thay đổi cấu trúc.`
            : report.new_changes.length
              ? `Phát hiện ${report.new_changes.length} thay đổi mới, không có thay đổi chặn.`
              : "Cấu trúc nguồn không đổi so với bản chuẩn.",
      );
    } catch (exc) {
      setError(messageOf(exc));
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr data-inactive={!source.enabled || undefined}>
      <td>
        <strong>{source.name}</strong>
        <div className="muted small">{KINDS[source.kind]}</div>
        {isAdmin && source.secret_ref && <div className="muted small mono">tham chiếu: {source.secret_ref}</div>}
      </td>
      <td>{source.department_name}</td>
      <td>
        <span
          className={`badge ${source.sensitivity === "high" ? "danger" : source.sensitivity === "medium" ? "warn" : "ok"}`}
        >
          {SENSITIVITY[source.sensitivity]}
        </span>
      </td>
      <td>
        {isAdmin ? (
          <select
            aria-label={`Mức AI được thấy ở ${source.name}`}
            value={source.llm_access_effective}
            disabled={busy}
            onChange={(e) => update({ llm_access: e.target.value as LLMAccess })}
          >
            {allowedAccess(source.sensitivity).map((a) => (
              <option key={a} value={a}>
                {ACCESS[a]}
              </option>
            ))}
          </select>
        ) : (
          source.access_text
        )}
      </td>
      <td className="mono small">{source.allowed_tables.join(", ")}</td>
      <td>
        {isAdmin ? (
          <button
            type="button"
            className="btn small"
            disabled={busy}
            onClick={() => update({ enabled: !source.enabled })}
          >
            {source.enabled ? "Tắt nguồn" : "Bật nguồn"}
          </button>
        ) : source.enabled ? (
          "Đang bật"
        ) : (
          "Đang tắt"
        )}
        {canCheck && source.enabled && (
          <button type="button" className="btn small" disabled={busy} onClick={checkDrift}>
            Kiểm tra lại cấu trúc
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

function Departments({ onDone }: { onDone: () => Promise<void> }) {
  const toast = useToast();
  const { data, error, loading, refresh } = usePoll<Department[]>("/departments", null);
  const [name, setName] = useState("");
  const [failure, setFailure] = useState("");

  async function create(event: FormEvent) {
    event.preventDefault();
    setFailure("");
    try {
      await apiPost("/departments", { name });
      toast(`Đã tạo phòng ban "${name}".`);
      setName("");
      await refresh();
      await onDone();
    } catch (exc) {
      setFailure(messageOf(exc));
    }
  }

  return (
    <Card title="Phòng ban">
      {loading && !data ? (
        <Loading text="Đang tải phòng ban…" />
      ) : !data ? (
        <ErrorBox message={error || "Không tải được danh sách."} onRetry={refresh} />
      ) : (
        <ul className="answered">
          {data.map((d) => (
            <li key={d.id}>
              <strong>{d.name}</strong>
            </li>
          ))}
        </ul>
      )}
      <form className="row" onSubmit={create} style={{ gap: 8, marginTop: 12 }}>
        <input
          aria-label="Tên phòng ban mới"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Tên phòng ban mới"
          maxLength={80}
        />
        <button type="submit" className="btn primary" disabled={name.trim().length < 2}>
          Tạo phòng ban
        </button>
      </form>
      {failure && <ErrorBox message={failure} />}
    </Card>
  );
}

export default function SourcesPage() {
  const { user } = useApp();
  const isAdmin = user?.role === "admin";
  const { data, error, loading, refresh } = usePoll<SourceView[]>("/sources", null);
  const departments = usePoll<Department[]>(isAdmin ? "/departments" : null, null);

  return (
    <div className="stack">
      <header className="page-head">
        <h1>Nguồn dữ liệu</h1>
        <p className="muted">
          Nguồn đã đăng ký và mức dữ liệu AI được xem.{" "}
          {isAdmin ? "Bạn thấy mọi nguồn." : "Bạn chỉ thấy nguồn của phòng ban mình."} AI không bao giờ thấy mật khẩu,
          khóa hay chuỗi kết nối.
        </p>
      </header>
      {isAdmin && departments.data && <RegisterForm departments={departments.data} onDone={refresh} />}
      <Card title="Nguồn đã đăng ký">
        {loading && !data ? (
          <Loading text="Đang tải nguồn dữ liệu…" />
        ) : !data ? (
          <ErrorBox message={error || "Không tải được danh sách."} onRetry={refresh} />
        ) : data.length === 0 ? (
          <Empty icon="sources">Bạn chưa được cấp quyền xem nguồn nào. Liên hệ quản trị viên.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Nguồn</th>
                  <th>Phòng ban</th>
                  <th>Độ nhạy cảm</th>
                  <th>AI được thấy</th>
                  <th>Bảng được phép</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {data.map((s) => (
                  <SourceRow key={s.id} source={s} isAdmin={isAdmin} onDone={refresh} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {isAdmin && <Departments onDone={departments.refresh} />}
    </div>
  );
}
