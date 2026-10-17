import type { Metadata } from "next";
import Link from "next/link";

import { DocsThemeToggle } from "@/components/docs/DocsTools";
import { Icon, SparkIcon } from "@/components/icons";
import type { IconName } from "@/lib/icons";
import {
  PROJECT_STATUS,
  PROJECT_TEAM,
  STATUS_TEXT,
  progressOf,
  type ItemStatus,
  type ProjectItem,
} from "@/lib/projectStatus";

// Trang tài liệu công khai (không cần đăng nhập; AppShell bỏ qua kiểm tra phiên). Viết cho người không rành kỹ thuật:
// mỗi ý tối đa 60 từ, không nêu địa chỉ API, cấu hình hay chi tiết nội bộ. Tiến độ đọc từ lib/projectStatus.ts.

export const metadata: Metadata = {
  title: "Tài liệu dự án · P-113 Pipeline Agent",
  description:
    "P-113 Pipeline Agent biến một câu yêu cầu thành bảng số liệu: agent viết code, chạy thử an toàn, người duyệt xem lại trước khi dùng thật.",
};

const TOC = [
  { id: "san-pham", label: "Sản phẩm là gì" },
  { id: "dung-thu", label: "Dùng thử 3 bước" },
  { id: "tien-do", label: "Tiến độ" },
  { id: "gioi-han", label: "Giới hạn hiện tại" },
  { id: "cong-nghe", label: "Công nghệ" },
  { id: "nhom", label: "Nhóm thực hiện" },
];

const TRY_STEPS = [
  {
    title: "Mở chế độ khách",
    text: "Bấm “Dùng thử, không cần đăng nhập”. Bạn vào ngay trang chủ với dữ liệu mẫu, không cần tài khoản.",
  },
  {
    title: "Gửi một yêu cầu",
    text: "Trong khung Yêu cầu mới, bấm “Thử ngay với ví dụ” rồi “Bắt đầu ngay”. Trả lời câu hỏi của agent và đồng ý kế hoạch.",
  },
  {
    title: "Duyệt như một Reviewer",
    text: "Khi lần chạy chờ duyệt, đổi vai sang Reviewer ở dải trên cùng, mở tab Duyệt code và bấm Duyệt.",
  },
];

const LIMITS = [
  {
    title: "Chế độ khách là dữ liệu mẫu",
    text: "Mọi kết quả trong chế độ khách được dựng sẵn từ một lần chạy thử, không do AI chạy thật. Thao tác của bạn chỉ lưu trong tab trình duyệt đang mở.",
  },
  {
    title: "Chạy thật cần đăng nhập",
    text: "Để AI viết code cho yêu cầu của bạn trên dữ liệu thật, cần tài khoản do quản trị viên cấp.",
  },
  {
    title: "Không tự đưa lên hệ thống thật",
    text: "Pipeline chỉ chạy thử trên bản sao dữ liệu. Đưa vào dùng thật luôn cần người duyệt đồng ý.",
  },
];

// Lấy từ mã nguồn thực tế (frontend/package.json, requirements.txt).
const TECH = [
  { name: "Next.js và React", text: "Dựng giao diện web bạn đang xem." },
  { name: "FastAPI (Python)", text: "Máy chủ nhận yêu cầu từ web và điều phối agent." },
  { name: "LangGraph", text: "Xếp các bước của agent thành một quy trình, có chỗ dừng chờ người quyết định." },
  {
    name: "Mô hình AI (OpenAI, Anthropic, Google Gemini)",
    text: "Đọc yêu cầu, lập kế hoạch và viết code; có thể đổi nhà cung cấp.",
  },
  { name: "dbt", text: "Cách viết các bước tính toán dữ liệu bằng SQL, kèm bài kiểm tra." },
  { name: "Airflow (DAG)", text: "Lịch cho pipeline tự chạy; agent viết sẵn file lịch này." },
  { name: "DuckDB", text: "Cơ sở dữ liệu nhỏ dùng làm sandbox để chạy thử an toàn." },
  { name: "sqlglot", text: "Đọc câu SQL để kiểm tra an toàn và tìm chỗ chạy chậm." },
  { name: "PostgreSQL", text: "Lưu tài khoản và lịch sử các lần chạy." },
  { name: "Monaco Editor", text: "Khung xem code và so sánh thay đổi ngay trên web." },
];

const STATUS_ICON: Record<ItemStatus, IconName> = {
  done: "success",
  doing: "pending",
  todo: "skipped",
  unknown: "unknown",
};

function StatusLabel({ status }: { status: ItemStatus }) {
  return (
    <span className="docs-status" data-status={status}>
      <Icon name={STATUS_ICON[status]} size={16} weight="bold" /> {STATUS_TEXT[status]}
    </span>
  );
}

function Progress({ items }: { items: ProjectItem[] }) {
  const { done, total, pct } = progressOf(items);
  const groups = [...new Set(items.map((item) => item.group))];
  return (
    <>
      <div className="docs-progress">
        <p className="docs-progress-label">
          <strong>
            {done}/{total} mục đã xong
          </strong>
        </p>
        <div
          className="docs-progress-bar"
          role="progressbar"
          aria-label="Tiến độ dự án"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={done}
          aria-valuetext={`${done} trên ${total} mục đã xong`}
        >
          <span style={{ width: `${pct}%` }} />
        </div>
      </div>
      {groups.map((group) => (
        <div key={group} className="docs-group">
          <h3>{group}</h3>
          <ul className="docs-items">
            {items
              .filter((item) => item.group === group)
              .map((item) => (
                <li key={item.title}>
                  <span className="docs-item-title">{item.title}</span>
                  <StatusLabel status={item.status} />
                  {item.note && <span className="docs-item-note">{item.note}</span>}
                </li>
              ))}
          </ul>
        </div>
      ))}
    </>
  );
}

export default function DocsPage() {
  return (
    <div className="docs-page">
      <header className="docs-top">
        <Link href="/" className="docs-brand">
          <SparkIcon size={22} />
          <span>P-113 Agent Studio</span>
        </Link>
        <nav className="docs-top-links" aria-label="Liên kết nhanh">
          <Link href="/demo" className="docs-link">
            Dùng thử
          </Link>
          <Link href="/login" className="docs-link">
            Đăng nhập
          </Link>
          <DocsThemeToggle />
        </nav>
      </header>

      <div className="docs-layout">
        <nav className="docs-toc" aria-label="Mục lục">
          <p className="docs-toc-title">Mục lục</p>
          <ol>
            {TOC.map((item) => (
              <li key={item.id}>
                <a href={`#${item.id}`}>{item.label}</a>
              </li>
            ))}
          </ol>
        </nav>

        <main className="docs-main" id="main">
          <h1>Tài liệu dự án</h1>

          <section id="san-pham" aria-labelledby="san-pham-title">
            <h2 id="san-pham-title">Sản phẩm là gì</h2>
            <p>
              P-113 Pipeline Agent giúp bạn có bảng số liệu chỉ bằng cách mô tả nó bằng lời. Agent hỏi lại chỗ chưa rõ,
              viết code lấy và tính dữ liệu, rồi chạy thử trên một bản sao dữ liệu tách riêng. Một người duyệt xem lại
              thay đổi trước khi pipeline được dùng thật.
            </p>
            <div className="docs-actions">
              <Link href="/demo" className="docs-btn primary">
                Dùng thử, không cần đăng nhập
              </Link>
              <Link href="/login" className="docs-btn">
                Đăng nhập
              </Link>
            </div>
          </section>

          <section id="dung-thu" aria-labelledby="dung-thu-title">
            <h2 id="dung-thu-title">Dùng thử 3 bước</h2>
            <ol className="docs-steps">
              {TRY_STEPS.map((step) => (
                <li key={step.title}>
                  <strong>{step.title}</strong>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>
          </section>

          <section id="tien-do" aria-labelledby="tien-do-title">
            <h2 id="tien-do-title">Tiến độ</h2>
            <Progress items={PROJECT_STATUS} />
          </section>

          <section id="gioi-han" aria-labelledby="gioi-han-title">
            <h2 id="gioi-han-title">Giới hạn hiện tại</h2>
            <ul className="docs-cards">
              {LIMITS.map((item) => (
                <li key={item.title}>
                  <strong>{item.title}</strong>
                  <p>{item.text}</p>
                </li>
              ))}
            </ul>
          </section>

          <section id="cong-nghe" aria-labelledby="cong-nghe-title">
            <h2 id="cong-nghe-title">Công nghệ</h2>
            <dl className="docs-tech">
              {TECH.map((item) => (
                <div key={item.name}>
                  <dt>{item.name}</dt>
                  <dd>{item.text}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section id="nhom" aria-labelledby="nhom-title">
            <h2 id="nhom-title">Nhóm thực hiện</h2>
            <ul className="docs-team">
              {PROJECT_TEAM.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </section>
        </main>
      </div>
    </div>
  );
}
