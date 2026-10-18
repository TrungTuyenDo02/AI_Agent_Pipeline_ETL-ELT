import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { DocsSectionNav } from "@/components/docs/DocsSectionNav";
import { DocsReveal, DocsThemeToggle } from "@/components/docs/DocsTools";
import { Rich } from "@/components/docs/Rich";
import { PipeSmithWordmark } from "@/components/PipeSmithWordmark";
import { PipSprite } from "@/components/PipSprite";
import { Icon, SparkIcon } from "@/components/icons";
import { LANDING as L } from "@/content/landing";

// Trang "Giới thiệu dự án" công khai (không cần đăng nhập; AppShell bỏ qua kiểm tra phiên). Chữ nằm ở content/landing.ts.
// Nhịp màu theo khối: tối (hero) → sáng → nhạt màu nhấn → sáng → tối → sáng → nhạt → tối (lời mời cuối trang).
// Khối tối (.docs-band) đặt lại token bằng giá trị tối (styles/tokens.css), nên luôn tối cả khi giao diện đang sáng.
// Server Component: chỉ thanh liên kết neo, nút sáng/tối và hiệu ứng hiện dần là Client Component.

export const metadata: Metadata = L.meta;

/** Ảnh chụp chế độ khách (dữ liệu mẫu), một bản sáng và một bản tối; CSS chọn bản theo giao diện đang dùng. */
function Shot({
  name,
  alt,
  width,
  height,
  sizes,
}: {
  name: string;
  alt: string;
  width: number;
  height: number;
  sizes: string;
}) {
  return (
    <span className="docs-shot-frame">
      <Image
        className="docs-shot-light"
        src={`/docs/${name}-light.webp`}
        alt={alt}
        width={width}
        height={height}
        sizes={sizes}
      />
      <Image
        className="docs-shot-dark"
        src={`/docs/${name}-dark.webp`}
        alt={alt}
        width={width}
        height={height}
        sizes={sizes}
      />
    </span>
  );
}

function DemoButton({ label = L.hero.cta }: { label?: string }) {
  return (
    <Link href="/demo" className="btn primary docs-cta">
      {label} <Icon name="start" size={18} weight="bold" />
    </Link>
  );
}

function SectionHead({
  id,
  kicker,
  title,
  children,
}: {
  id: string;
  kicker: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="docs-section-head" data-reveal>
      <p className="docs-kicker">{kicker}</p>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </header>
  );
}

export default function DocsPage() {
  return (
    <div className="docs-page">
      <DocsReveal />
      <a href="#tong-quan" className="skip-link">
        {L.skip}
      </a>
      <header className="docs-top">
        <div className="docs-container docs-top-inner">
          <Link href="/" className="docs-brand">
            <SparkIcon size={22} className="brand-spark" />
            <PipeSmithWordmark />
          </Link>
          <nav className="docs-top-links" aria-label={L.quickLinks}>
            <Link href="/login" className="btn docs-top-btn">
              {L.login}
            </Link>
            <DocsThemeToggle />
          </nav>
        </div>
      </header>

      <DocsSectionNav items={L.sections} />

      <main className="docs-main" id="main">
        <section id="tong-quan" className="docs-section docs-band docs-overview" aria-labelledby="tong-quan-title">
          <div className="docs-container docs-hero">
            <div className="docs-hero-text">
              <p className="docs-kicker">{L.hero.kicker}</p>
              <h1 id="tong-quan-title">{L.hero.title}</h1>
              <div className="pip-intro">
                <PipSprite pose="notes" size={80} label="Pip đang ghi chép yêu cầu" />
                <div className="pip-intro-copy">
                  <strong>Pip, người bạn nhỏ của PipeSmith</strong>
                  <p>Ghi chép, làm việc và chờ bạn duyệt từng bước.</p>
                </div>
              </div>
              <p className="docs-lead">
                <Rich text={L.hero.lead} />
              </p>
              <div className="docs-actions">
                <DemoButton />
                <a href="#quy-trinh" className="docs-text-link">
                  {L.hero.secondary}
                </a>
              </div>
              <p className="docs-note">
                <Icon name="info" size={16} />
                <span>
                  <Rich text={L.hero.note} />
                </span>
              </p>
            </div>
            <figure className="docs-hero-shot">
              <Shot name="run" alt={L.hero.shotAlt} width={1244} height={760} sizes="(max-width: 960px) 100vw, 700px" />
              <figcaption>{L.hero.shotCaption}</figcaption>
            </figure>
          </div>
          <div className="docs-container">
            <ul className="docs-cards docs-overview-cards">
              {L.overview.map((item) => (
                <li key={item.title} className="docs-card" data-tone={item.tone}>
                  <span className="docs-card-icon" aria-hidden="true">
                    <Icon name={item.icon} size={20} />
                  </span>
                  <h3>{item.title}</h3>
                  <p>
                    <Rich text={item.text} />
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="cach-hoat-dong" className="docs-section" aria-labelledby="cach-hoat-dong-title">
          <div className="docs-container">
            <SectionHead id="cach-hoat-dong" kicker={L.how.kicker} title={L.how.title} />
            <ol className="docs-how">
              {L.how.steps.map((step, index) => (
                <li key={step.title} className="docs-card" data-tone={step.tone} data-reveal>
                  <span className="docs-card-icon" aria-hidden="true">
                    <Icon name={step.icon} size={22} />
                  </span>
                  <span className="docs-how-num">{String(index + 1).padStart(2, "0")}</span>
                  <h3>{step.title}</h3>
                  <p>
                    <Rich text={step.text} />
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="demo" className="docs-section docs-tinted" aria-labelledby="demo-title">
          <div className="docs-container">
            <SectionHead id="demo" kicker={L.demo.kicker} title={L.demo.title}>
              <p className="docs-intro">
                <Rich text={L.demo.intro} />
              </p>
            </SectionHead>
            <div className="docs-split" data-reveal>
              <div>
                <blockquote className="docs-request">
                  <span>{L.demo.requestLabel}</span>
                  {L.demo.request}
                </blockquote>
                <h3>{L.demo.pointsTitle}</h3>
                <ul className="docs-points">
                  {L.demo.points.map((point) => (
                    <li key={point.text}>
                      <Icon name={point.icon} size={20} />
                      <span>
                        <Rich text={point.text} />
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="docs-muted">
                  <Rich text={L.demo.note} />
                </p>
                <DemoButton label={L.demo.cta} />
              </div>
              <figure className="docs-figure">
                <Shot
                  name="review"
                  alt={L.demo.shotAlt}
                  width={1244}
                  height={720}
                  sizes="(max-width: 960px) 100vw, 640px"
                />
                <figcaption>{L.demo.shotCaption}</figcaption>
              </figure>
            </div>
          </div>
        </section>

        <section id="quy-trinh" className="docs-section" aria-labelledby="quy-trinh-title">
          <div className="docs-container">
            <SectionHead id="quy-trinh" kicker={L.flow.kicker} title={L.flow.title} />
            <ol className="docs-flow">
              {L.flow.steps.map((step, index) => (
                <li key={step.title} data-reveal>
                  <span className="docs-flow-num" aria-hidden="true">
                    {index + 1}
                  </span>
                  <h3>{step.title}</h3>
                  <p>
                    <Rich text={step.text} />
                  </p>
                  <p className="docs-actors">
                    <span className="sr-only">{L.flow.actorsLabel}</span>
                    {step.actors.map((actor) => (
                      <span key={actor} className="docs-actor" data-actor={actor}>
                        {L.flow.actors[actor]}
                      </span>
                    ))}
                  </p>
                </li>
              ))}
            </ol>

            <div className="docs-principle" data-reveal>
              <div>
                <h3>{L.flow.principleTitle}</h3>
                <p className="docs-muted">
                  <Rich text={L.flow.principleText} />
                </p>
              </div>
              <ul>
                {L.flow.principle.map((item) => (
                  <li key={item.actor} data-actor={item.actor}>
                    <strong>{item.title}</strong>
                    <span>{item.text}</span>
                  </li>
                ))}
              </ul>
            </div>

            <p className="docs-callout" data-reveal>
              <Icon name="info" size={18} />
              <span>
                <Rich text={L.flow.callout} />
              </span>
            </p>
          </div>
        </section>

        <section id="ky-thuat" className="docs-section docs-band" aria-labelledby="ky-thuat-title">
          <div className="docs-container">
            <SectionHead id="ky-thuat" kicker={L.techniques.kicker} title={L.techniques.title} />
            <ul className="docs-cards docs-features">
              {L.techniques.items.map((item) => (
                <li key={item.title} className="docs-card" data-tone={item.tone} data-reveal>
                  <span className="docs-card-icon" aria-hidden="true">
                    <Icon name={item.icon} size={22} />
                  </span>
                  <h3>{item.title}</h3>
                  <p>
                    <Rich text={item.does} />
                  </p>
                  <p className="docs-feature-help">
                    <strong>{L.techniques.helpsLabel}</strong> {item.helps}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="cong-nghe" className="docs-section" aria-labelledby="cong-nghe-title">
          <div className="docs-container">
            <SectionHead id="cong-nghe" kicker={L.tech.kicker} title={L.tech.title} />
            <div className="docs-tech-groups">
              {L.tech.groups.map((group) => (
                <div key={group.role} className="docs-card" data-tone={group.tone} data-reveal>
                  <h3>
                    <span className="docs-card-icon" aria-hidden="true">
                      <Icon name={group.icon} size={18} />
                    </span>
                    {group.role}
                  </h3>
                  <dl className="docs-tech">
                    {group.items.map((item) => (
                      <div key={item.name}>
                        <dt>{item.name}</dt>
                        <dd>{item.text}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ))}
            </div>
            <div className="docs-output" data-reveal>
              <h3>
                <Icon name="file" size={18} /> {L.tech.outputTitle}
              </h3>
              <dl className="docs-tech docs-tech-row">
                {L.tech.output.map((item) => (
                  <div key={item.name}>
                    <dt>{item.name}</dt>
                    <dd>
                      <Rich text={item.text} />
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        <section id="huong-di" className="docs-section docs-tinted" aria-labelledby="huong-di-title">
          <div className="docs-container">
            <SectionHead id="huong-di" kicker={L.roadmap.kicker} title={L.roadmap.title}>
              <p className="docs-intro">
                <Rich text={L.roadmap.intro} />
              </p>
            </SectionHead>
            <ol className="docs-roadmap">
              {L.roadmap.items.map((item) => (
                <li key={item.title} data-reveal>
                  <h3>{item.title}</h3>
                  <p>
                    <Rich text={item.text} />
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="docs-section docs-band docs-end" aria-labelledby="docs-end-title">
          <div className="docs-container docs-end-inner" data-reveal>
            <div>
              <h2 id="docs-end-title">{L.end.title}</h2>
              <p>
                <Rich text={L.end.text} />
              </p>
            </div>
            <DemoButton label={L.end.cta} />
          </div>
        </section>
      </main>
    </div>
  );
}
