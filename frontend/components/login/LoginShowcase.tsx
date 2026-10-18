"use client";

import { DEMO_ACCOUNTS, SHOW_DEMO_ACCOUNTS, type LoginText } from "@/lib/loginText";

import { Icon } from "../icons";

/**
 * Khung trình diễn của trang đăng nhập (bên phải form), kiểu canvas: ít chữ, nhiều hình.
 * Từ trên xuống: ba điểm nổi bật, luồng làm việc (màu theo ai làm: agent, code hay người), công cụ,
 * bốn con số đo được (phần trăm lớn, số gốc nhỏ bên dưới), tài khoản demo.
 * Câu giải thích dài nằm ở `title` của từng nút (hiện khi rê chuột), không chiếm chỗ trên canvas.
 */
export function LoginShowcase({
  t,
  onPickAccount,
}: {
  t: LoginText;
  onPickAccount: (user: string, password: string) => void;
}) {
  return (
    <section className="canvas" aria-label={t.canvasLabel}>
      <ul className="canvas-points" aria-label={t.pointsLabel}>
        {t.points.map((point) => (
          <li key={point.icon}>
            <Icon name={point.icon} size={20} weight="fill" />
            <strong>{point.title}</strong>
            <span>{point.text}</span>
          </li>
        ))}
      </ul>

      <ol className="canvas-flow" aria-label={t.flowLabel}>
        {t.flow.map((node, index) => (
          <li
            key={node.code}
            className={`canvas-node ${node.kind}`}
            title={node.hint}
            style={{ animationDelay: `${index * 0.28}s` }}
          >
            <span className="canvas-code">{node.code}</span>
            <strong>{node.label}</strong>
          </li>
        ))}
      </ol>
      <ul className="canvas-legend" aria-label={t.legendLabel}>
        {t.legend.map((item) => (
          <li key={item.kind} className={item.kind}>
            <i aria-hidden="true" />
            {item.label}
          </li>
        ))}
      </ul>

      <ul className="canvas-tools" aria-label={t.toolsLabel}>
        {t.tools.map((tool) => (
          <li key={tool}>{tool}</li>
        ))}
      </ul>

      <ul className="canvas-stats" aria-label={t.statsLabel}>
        {t.highlights.map((item) => (
          <li key={item.label} title={item.hint}>
            <b>{item.value}</b>
            <span>{item.label}</span>
            <small>{item.detail}</small>
          </li>
        ))}
      </ul>

      {SHOW_DEMO_ACCOUNTS && (
        <div className="canvas-accounts" title={t.accountsHint}>
          <span>
            <Icon name="users" size={16} weight="fill" /> {t.accountsTitle}
          </span>
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
        </div>
      )}
    </section>
  );
}
