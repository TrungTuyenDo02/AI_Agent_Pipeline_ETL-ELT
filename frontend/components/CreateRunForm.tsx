"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { apiPost, messageOf } from "@/lib/api";
import type { Accepted } from "@/lib/types";

import { ErrorBox } from "./ui";

const EXAMPLES = [
  "Gộp đơn hàng 3 nguồn, tính doanh thu ngày",
  "Doanh thu theo ngày và theo nguồn bán, chỉ tính đơn đã giao",
  "Số đơn và giá trị trung bình mỗi đơn theo tháng",
];

export function CreateRunForm() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const tooShort = text.trim().length < 5;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (tooShort || sending) return;
    setSending(true);
    setError("");
    try {
      const accepted = await apiPost<Accepted>("/runs", { request_text: text.trim() });
      router.push(`/runs/${accepted.run_id}`);
    } catch (exc) {
      setError(messageOf(exc));
      setSending(false);
    }
  }

  return (
    <form onSubmit={submit} className="stack" style={{ gap: 10 }}>
      <label htmlFor="request" className="sr-only">
        Yêu cầu pipeline
      </label>
      <textarea
        id="request"
        rows={3}
        maxLength={4000}
        placeholder="Mô tả bằng lời thường: cần bảng gì, từ nguồn nào, tính chỉ số gì… Agent sẽ hỏi lại nếu chưa rõ."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void submit(e);
        }}
      />
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="chips" aria-label="Ví dụ">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" className="chip" onClick={() => setText(example)}>
              {example}
            </button>
          ))}
        </div>
        <button type="submit" className="btn primary" disabled={tooShort || sending}>
          {sending ? "Đang gửi…" : "Gửi yêu cầu"}
        </button>
      </div>
      <small className="muted">Ctrl + Enter để gửi. Agent chỉ chạy trong sandbox DuckDB, không đụng production.</small>
      {error && <ErrorBox message={error} />}
    </form>
  );
}
