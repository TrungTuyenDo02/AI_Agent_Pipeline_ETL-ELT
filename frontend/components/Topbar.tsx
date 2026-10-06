"use client";

import { useState, type FormEvent } from "react";

import type { Role } from "@/lib/types";

import { useApp, type ThemeChoice } from "./AppContext";

const THEME_LABELS: Record<ThemeChoice, string> = { system: "Theo máy", light: "Sáng", dark: "Tối" };
const NAME_PATTERN = /^[A-Za-z0-9._-]{1,32}$/;

function ModeBadges() {
  const { status, statusError } = useApp();
  if (statusError) return <span className="badge danger">Mất kết nối API</span>;
  if (!status) return <span className="badge muted">Đang kiểm tra API…</span>;
  return (
    <>
      {status.simulated ? (
        <span className="badge warn" title="LLM_PROVIDER=mock: câu trả lời LLM là cố định, không phải chất lượng thật">
          Chế độ mô phỏng
        </span>
      ) : (
        <span className="badge ok" title={status.models}>
          LLM thật: {status.llm_provider}
        </span>
      )}
      <span className="badge muted">
        {status.require_separate_reviewer ? "Chế độ 2 người duyệt" : "1 vai trò DE (tự duyệt)"}
      </span>
    </>
  );
}

function UserBox() {
  const { user, setUser, status } = useApp();
  const [name, setName] = useState<string | null>(null);
  const separate = status?.require_separate_reviewer ?? false;
  const draft = name ?? user.name;
  const valid = NAME_PATTERN.test(draft);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (valid) setUser({ ...user, name: draft });
    setName(null);
  }

  return (
    <form className="userbox" onSubmit={submit}>
      <label htmlFor="user-name">Người dùng</label>
      <input
        id="user-name"
        value={draft}
        onChange={(e) => setName(e.target.value)}
        onBlur={submit}
        aria-invalid={!valid}
        title="Chữ không dấu, số, . _ - (tối đa 32 ký tự)"
        size={10}
      />
      {separate && (
        <select
          aria-label="Vai trò"
          value={user.role === "de" ? "engineer" : user.role}
          onChange={(e) => setUser({ ...user, role: e.target.value as Role })}
        >
          <option value="engineer">Engineer</option>
          <option value="reviewer">Reviewer</option>
        </select>
      )}
    </form>
  );
}

export function Topbar() {
  const { theme, setTheme } = useApp();
  return (
    <header className="topbar">
      <div className="topbar-badges">
        <ModeBadges />
      </div>
      <div className="topbar-tools">
        <UserBox />
        <div className="segmented" role="group" aria-label="Giao diện sáng hoặc tối">
          {(Object.keys(THEME_LABELS) as ThemeChoice[]).map((value) => (
            <button key={value} type="button" aria-pressed={theme === value} onClick={() => setTheme(value)}>
              {THEME_LABELS[value]}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
