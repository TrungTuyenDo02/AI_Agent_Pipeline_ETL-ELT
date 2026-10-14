"use client";

import { useState } from "react";

import { DEMO_ACCOUNTS, DEMO_COMMAND, SHOW_DEMO_ACCOUNTS, type LoginText } from "@/lib/loginText";

import { Icon } from "../icons";

function CopyCommand({ text, t }: { text: string; t: LoginText }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1600);
    } catch {
      // trình duyệt chặn clipboard: người dùng tự bôi đen và chép
    }
  }
  return (
    <div className="hero-cmd">
      <code>{text}</code>
      <button type="button" onClick={copy} aria-label={t.copy}>
        <Icon name={done ? "check" : "copy"} size={16} />
        <span>{done ? t.copied : t.copy}</span>
      </button>
    </div>
  );
}

/**
 * Khung thông tin dự án bên trái trang đăng nhập, bố cục kiểu canvas: một tấm bảng có lưới chấm, các thẻ nằm sẵn
 * trên bảng và hiện hết cùng lúc (luồng agent nối bằng mũi tên, rồi thẻ Chạy thử, Dữ liệu mẫu, Tài khoản demo).
 */
export function LoginShowcase({
  t,
  onPickAccount,
}: {
  t: LoginText;
  onPickAccount: (user: string, password: string) => void;
}) {
  return (
    <section className="canvas" aria-label={t.tabsLabel}>
      <ol className="canvas-flow" aria-label={t.tabs.about}>
        {t.about.map((item, index) => (
          <li key={item.title} className="canvas-node">
            <span className="hero-step-num">{index + 1}</span>
            <strong>{item.title}</strong>
            <small>{item.text}</small>
          </li>
        ))}
      </ol>
      <p className="canvas-rule">
        <Icon name="reviewer" size={16} weight="fill" /> {t.aboutNote}
      </p>

      <div className="canvas-cards">
        <article className="canvas-card">
          <h3>
            <Icon name="sandbox" size={16} weight="fill" /> {t.tabs.run}
          </h3>
          <ol className="canvas-steps">
            {t.runSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <CopyCommand text={DEMO_COMMAND} t={t} />
        </article>

        <article className="canvas-card">
          <h3>
            <Icon name="sources" size={16} weight="fill" /> {t.tabs.data}
          </h3>
          <ul className="canvas-data">
            {t.datasets.map((set) => (
              <li key={set.name}>
                <strong>{set.name}</strong>
                <small>{set.detail}</small>
              </li>
            ))}
          </ul>
          <p className="hero-note">{t.dataNote}</p>
        </article>

        {SHOW_DEMO_ACCOUNTS && (
          <article className="canvas-card canvas-card-wide">
            <h3>
              <Icon name="users" size={16} weight="fill" /> {t.accountsTitle}
            </h3>
            <p className="hero-note">{t.accountsHint}</p>
            <div className="hero-account-list">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.user}
                  type="button"
                  onClick={() => onPickAccount(account.user, account.password)}
                  aria-label={`${t.roles[account.role]}: ${account.user}`}
                >
                  <Icon
                    name={account.role === "engineer" ? "engineer" : account.role === "reviewer" ? "reviewer" : "users"}
                    size={16}
                  />
                  <span>{account.user}</span>
                  <em>{t.roles[account.role]}</em>
                </button>
              ))}
            </div>
          </article>
        )}
      </div>
    </section>
  );
}
