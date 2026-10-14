"use client";

import { useState, type FormEvent } from "react";

import type { ClarifyQuestion, SchemaReport } from "@/lib/types";

import { useHasRole } from "../AppContext";
import { RoleNote } from "../Topbar";
import { Checkbox, ErrorBox } from "../ui";
import { useRun } from "./RunContext";

// Form cho các điểm dừng cần người: J1 trả lời câu hỏi làm rõ, cứu hộ. (J1b: PlanReview; J2: màn duyệt.)

export function ClarifyForm({ unknowns, questions }: { unknowns: string[]; questions: ClarifyQuestion[] }) {
  const { act } = useRun();
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const complete = questions.every((q) => answers[q.id]?.length);
  const engineer = useHasRole("engineer");

  // Câu chọn nhiều: bật/tắt một giá trị, giữ thứ tự như danh sách lựa chọn
  function toggle(q: ClarifyQuestion, option: string, on: boolean) {
    const current = Array.isArray(answers[q.id]) ? (answers[q.id] as string[]) : [];
    const next = q.options.filter((o) => (o === option ? on : current.includes(o)));
    setAnswers({ ...answers, [q.id]: next });
  }

  function isChecked(q: ClarifyQuestion, option: string) {
    const value = answers[q.id];
    return Array.isArray(value) ? value.includes(option) : value === option;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(await act("/answers", { answers }, "Đã gửi câu trả lời, agent chạy tiếp."));
    setSending(false);
  }

  return (
    <form onSubmit={submit}>
      <RoleNote need="engineer" />
      {unknowns.length > 0 && (
        <div className="alert info" style={{ marginBottom: 12 }}>
          <span>Agent chưa rõ: {unknowns.join("; ")}</span>
        </div>
      )}
      {questions.map((q, index) => (
        <fieldset key={q.id}>
          <legend>
            {index + 1}. {q.question}
          </legend>
          {q.multiple && (
            <p className="muted" style={{ margin: "0 0 8px" }}>
              Giá trị thật của cột {q.column}, chọn một hoặc nhiều. AI không thấy danh sách này, chỉ nhận giá trị bạn
              chọn.
            </p>
          )}
          <div className="option-pills">
            {q.options.map((option) => (
              <label key={option} className="option">
                <input
                  type={q.multiple ? "checkbox" : "radio"}
                  name={q.id}
                  value={option}
                  checked={isChecked(q, option)}
                  onChange={(event) =>
                    q.multiple ? toggle(q, option, event.target.checked) : setAnswers({ ...answers, [q.id]: option })
                  }
                />
                <span>{option}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      {error && <ErrorBox message={error} />}
      <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
        <button type="submit" className="btn primary" disabled={!complete || sending || !engineer}>
          {sending ? "Đang gửi…" : "Gửi câu trả lời"}
        </button>
      </div>
    </form>
  );
}

/** Cửa kiểm tra đầu vào hỏi bổ sung (câu hỏi theo mẫu cố định) hoặc xin viết lại yêu cầu. */
export function InputInfoForm({ message, rewrite }: { message: string; rewrite: boolean }) {
  const { act } = useRun();
  const engineer = useHasRole("engineer");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState("");

  async function send(action: "send" | "abort") {
    setSending(true);
    setFailure(
      await act(
        "/input",
        { action, text },
        action === "send" ? "Đã gửi, agent kiểm tra lại yêu cầu." : "Đã dừng lần chạy.",
      ),
    );
    setSending(false);
  }

  return (
    <div className="stack" style={{ gap: 10 }}>
      <RoleNote need="engineer" />
      <div className="alert info" style={{ whiteSpace: "pre-line" }}>
        <span>{message}</span>
      </div>
      <label htmlFor="input-info">{rewrite ? "Viết lại yêu cầu" : "Thông tin bổ sung"}</label>
      <textarea id="input-info" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} />
      {failure && <ErrorBox message={failure} />}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="button" className="btn danger" disabled={sending || !engineer} onClick={() => send("abort")}>
          Dừng lần chạy
        </button>
        <button
          type="button"
          className="btn primary"
          disabled={sending || !engineer || !text.trim()}
          onClick={() => send("send")}
        >
          Gửi
        </button>
      </div>
    </div>
  );
}

export function RescueForm({ error, attempts }: { error: string; attempts: number }) {
  const { act } = useRun();
  const [hint, setHint] = useState("");
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState("");
  const engineer = useHasRole("engineer");

  async function send(action: "retry" | "abort") {
    setSending(true);
    setFailure(
      await act("/rescue", { action, hint }, action === "retry" ? "Đã gửi gợi ý, agent thử lại." : "Đã dừng lần chạy."),
    );
    setSending(false);
  }

  return (
    <div className="stack" style={{ gap: 10 }}>
      <RoleNote need="engineer" />
      <p>Agent đã sửa {attempts} lần nhưng vẫn lỗi. Lỗi cuối (do V-node đo):</p>
      <pre>{error || "(không có chi tiết)"}</pre>
      <label htmlFor="hint">Gợi ý cho agent (ví dụ: cột ngày ở nguồn Tiki dạng dd/mm/yyyy)</label>
      <textarea id="hint" value={hint} onChange={(e) => setHint(e.target.value)} maxLength={2000} />
      {failure && <ErrorBox message={failure} />}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="button" className="btn danger" disabled={sending || !engineer} onClick={() => send("abort")}>
          Dừng lần chạy
        </button>
        <button
          type="button"
          className="btn primary"
          disabled={sending || !engineer || !hint.trim()}
          onClick={() => send("retry")}
        >
          Gửi gợi ý và thử lại
        </button>
      </div>
    </div>
  );
}

/** Mục 8: nguồn có cột bị xóa / nghi đổi tên. Engineer xác nhận từng cặp đổi tên (không tự đoán) hoặc dừng. */
export function SchemaForm({ report }: { report: SchemaReport }) {
  const { act } = useRun();
  const engineer = useHasRole("engineer");
  const [renames, setRenames] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState("");
  const changes = report.changes.filter((c) => Object.keys(c.removed).length > 0);

  async function send(action: "continue" | "abort") {
    setSending(true);
    setFailure(
      await act(
        "/schema",
        { action, renames: action === "continue" ? renames : {} },
        action === "continue" ? "Đã xác nhận cấu trúc mới, agent chạy tiếp." : "Đã dừng lần chạy.",
      ),
    );
    setSending(false);
  }

  function toggle(oldName: string, newName: string, on: boolean) {
    const next = { ...renames };
    if (on) next[oldName] = newName;
    else delete next[oldName];
    setRenames(next);
  }

  return (
    <div className="stack" style={{ gap: 12 }}>
      <RoleNote need="engineer" />
      <p>
        Nguồn dữ liệu đã <strong>mất cột</strong> so với bản Reviewer duyệt lần trước. Agent không tự đoán cột nào đổi
        tên: hãy xác nhận từng cặp, hoặc dừng để kiểm tra nguồn.
      </p>
      {changes.map((change) => (
        <div key={change.source} className="schema-box">
          <strong className="mono">{change.source}</strong>
          <ul className="schema-cols">
            {Object.entries(change.removed).map(([col, type]) => (
              <li key={col}>
                <span className="badge danger">− {col}</span> <span className="muted small">{type}</span>
              </li>
            ))}
          </ul>
          {change.rename_candidates.map(([oldName, newName]) => (
            <Checkbox
              key={`${oldName}-${newName}`}
              checked={renames[oldName] === newName}
              disabled={!engineer || sending}
              onChange={(on) => toggle(oldName, newName, on)}
            >
              Đúng, <span className="mono">{oldName}</span> đã đổi tên thành <span className="mono">{newName}</span>
            </Checkbox>
          ))}
        </div>
      ))}
      <small className="muted">
        Chạy tiếp: mọi thay đổi cấu trúc và đề xuất sửa sẽ hiện lại cho Reviewer ở màn duyệt; cấu trúc mới chỉ thành
        chuẩn khi Reviewer duyệt lần chạy.
      </small>
      {failure && <ErrorBox message={failure} />}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="button" className="btn danger" disabled={sending || !engineer} onClick={() => send("abort")}>
          Dừng lần chạy
        </button>
        <button type="button" className="btn primary" disabled={sending || !engineer} onClick={() => send("continue")}>
          Xác nhận và chạy tiếp
        </button>
      </div>
    </div>
  );
}
