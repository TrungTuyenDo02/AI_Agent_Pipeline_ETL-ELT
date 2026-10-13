"use client";

import { useState } from "react";

import { DEMO_ACCOUNTS, DEMO_COMMAND, SHOW_DEMO_ACCOUNTS, type LoginText } from "@/lib/loginText";

import { Icon } from "../icons";

type Tab = "about" | "run" | "data";
const TAB_ICON = { about: "agent", run: "sandbox", data: "sources" } as const;

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

/** Khung thông tin dự án bên trái trang đăng nhập: giới thiệu, hướng dẫn chạy, dữ liệu mẫu. */
export function LoginShowcase({
  t,
  onPickAccount,
}: {
  t: LoginText;
  onPickAccount: (user: string, password: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("about");
  const tabs: Tab[] = ["about", "run", "data"];
  return (
    <section className="hero-info" aria-label={t.tabsLabel}>
      <div className="hero-tabs" role="tablist" aria-label={t.tabsLabel}>
        {tabs.map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`hero-tab-${id}`}
            aria-selected={tab === id}
            aria-controls="hero-panel"
            className={tab === id ? "hero-tab active" : "hero-tab"}
            onClick={() => setTab(id)}
          >
            <Icon name={TAB_ICON[id]} size={16} weight={tab === id ? "fill" : "regular"} />
            {t.tabs[id]}
          </button>
        ))}
      </div>
      <div className="hero-panel" id="hero-panel" role="tabpanel" aria-labelledby={`hero-tab-${tab}`}>
        {tab === "about" && (
          <>
            <ol className="hero-flow">
              {t.about.map((item, index) => (
                <li key={item.title}>
                  <span className="hero-step-num">{index + 1}</span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.text}</small>
                  </span>
                </li>
              ))}
            </ol>
            <p className="hero-note">{t.aboutNote}</p>
          </>
        )}
        {tab === "run" && (
          <>
            <ol className="hero-steps">
              {t.runSteps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p className="hero-note">{t.runOpen}</p>
            <CopyCommand text={DEMO_COMMAND} t={t} />
            {SHOW_DEMO_ACCOUNTS && (
              <div className="hero-accounts">
                <strong>{t.accountsTitle}</strong>
                <small>{t.accountsHint}</small>
                <div className="hero-account-list">
                  {DEMO_ACCOUNTS.map((account) => (
                    <button
                      key={account.user}
                      type="button"
                      onClick={() => onPickAccount(account.user, account.password)}
                      aria-label={`${t.roles[account.role]}: ${account.user}`}
                    >
                      <Icon
                        name={
                          account.role === "engineer" ? "engineer" : account.role === "reviewer" ? "reviewer" : "users"
                        }
                        size={16}
                      />
                      <span>{account.user}</span>
                      <em>{t.roles[account.role]}</em>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
        {tab === "data" && (
          <>
            <p className="hero-note">{t.dataIntro}</p>
            <ul className="hero-data">
              {t.datasets.map((set) => (
                <li key={set.name}>
                  <Icon name="table" size={18} weight="duotone" />
                  <span>
                    <strong>{set.name}</strong>
                    <small>{set.detail}</small>
                  </span>
                </li>
              ))}
            </ul>
            <p className="hero-note">{t.dataNote}</p>
          </>
        )}
      </div>
    </section>
  );
}
