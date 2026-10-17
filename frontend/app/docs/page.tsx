import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { DocsSectionNav, type DocsSection } from "@/components/docs/DocsSectionNav";
import { DocsThemeToggle } from "@/components/docs/DocsTools";
import { Icon, SparkIcon } from "@/components/icons";
import type { IconName } from "@/lib/icons";

// Trang "Giới thiệu dự án" công khai (không cần đăng nhập; AppShell bỏ qua kiểm tra phiên). Viết cho người xem lần đầu:
// câu ngắn, giải thích thuật ngữ ở lần đầu, không nêu địa chỉ API, cấu hình, số đo hay thông tin nội bộ.
// Mỗi mô tả phải có căn cứ trong code; phân biệt rõ tính năng hiện có, chế độ khách (mô phỏng) và định hướng.
// Server Component: chỉ thanh liên kết neo (DocsSectionNav) và nút sáng/tối là Client Component.

export const metadata: Metadata = {
  title: "Giới thiệu dự án · P-113 Pipeline Agent",
  description:
    "P-113 thử nghiệm dùng AI hỗ trợ xây dựng và tối ưu pipeline dữ liệu: làm rõ yêu cầu, lập kế hoạch, sinh code, chạy thử và để người dùng duyệt.",
};

const SECTIONS: DocsSection[] = [
  { id: "tong-quan", label: "Tổng quan" },
  { id: "demo", label: "Demo" },
  { id: "quy-trinh", label: "Quy trình" },
  { id: "ky-thuat", label: "Kỹ thuật" },
  { id: "cong-nghe", label: "Công nghệ" },
  { id: "huong-di", label: "Hướng đi" },
];

const OVERVIEW: { title: string; text: string }[] = [
  {
    title: "Bài toán",
    text: "Dữ liệu nằm ở nhiều nguồn, mỗi nơi ghi một kiểu: đơn trùng, ngày lẫn định dạng, số tiền viết dạng chữ. Viết pipeline xử lý bằng tay tốn thời gian và dễ sai mà khó phát hiện.",
  },
  {
    title: "P-113 làm gì",
    text: "Pipeline dữ liệu là chuỗi bước tự động lấy dữ liệu từ các nguồn, làm sạch và tính ra bảng số liệu dùng được. P-113 để AI viết chuỗi bước đó, rồi chạy thử và đo kết quả bằng code.",
  },
  {
    title: "Điều hệ thống không làm",
    text: "Không chạy pipeline trên dữ liệu thật đang vận hành và không tự triển khai. Người dùng xem bằng chứng, duyệt, rồi tự đưa code vào quy trình triển khai của mình.",
  },
];

// Khớp kịch bản chế độ khách (lib/demo/fixtures.ts). Chỉ nêu điều riêng của demo; các bước chung nằm ở "Quy trình".
const DEMO_POINTS: { icon: IconName; text: string }[] = [
  {
    icon: "info",
    text: "Trả lời hai câu hỏi trắc nghiệm: đơn ở trạng thái nào được tính doanh thu, xử lý mã đơn trùng ra sao.",
  },
  { icon: "runs", text: "Mở các lần chạy mẫu ở nhiều trạng thái: đang chạy, chờ duyệt, đã dừng và đã duyệt." },
  {
    icon: "reviewer",
    text: "Đổi vai sang Reviewer ở dải trên cùng để xem diff, bằng chứng do code đo và bấm Duyệt (giả lập).",
  },
];

type Actor = "human" | "ai" | "code";

const ACTOR_TEXT: Record<Actor, string> = { human: "Con người", ai: "AI", code: "Code" };

const FLOW: { title: string; text: string; actors: Actor[] }[] = [
  {
    title: "Mô tả yêu cầu",
    text: "Bạn viết một câu về bảng số liệu cần có. Bước kiểm tra bằng code lọc trước câu rỗng, vô nghĩa hoặc lạc đề.",
    actors: ["human", "code"],
  },
  {
    title: "Làm rõ, duyệt kế hoạch",
    text: "AI hỏi lại chỗ chưa rõ rồi đề xuất kế hoạch: lấy nguồn nào, làm sạch ra sao, bảng kết quả có cột gì. Bạn đồng ý mới sang bước viết code.",
    actors: ["ai", "human"],
  },
  {
    title: "Sinh code và test",
    text: "AI viết model dbt, DAG Airflow và bài test. Phần viết test do một agent riêng làm, không xem code pipeline.",
    actors: ["ai"],
  },
  {
    title: "Chạy thử, kiểm tra, tối ưu",
    text: "Code chạy trong sandbox, tức một bản sao dữ liệu tách riêng. Máy kiểm tra kết quả, đối soát số liệu rồi thử cách viết truy vấn nhanh hơn.",
    actors: ["code", "ai"],
  },
  {
    title: "Người dùng duyệt",
    text: "Reviewer xem diff và bằng chứng, rồi quyết định duyệt hay yêu cầu sửa kèm ghi chú.",
    actors: ["human"],
  },
];

const PRINCIPLE: { actor: Actor; title: string; text: string }[] = [
  { actor: "human", title: "Con người quyết định", text: "Trả lời câu hỏi, duyệt kế hoạch, duyệt code." },
  { actor: "ai", title: "AI thực thi", text: "Hỏi lại, lập kế hoạch, viết code và test." },
  { actor: "code", title: "Code kiểm chứng", text: "Chạy thử, đo kết quả, so trước và sau. Không nhờ AI tự chấm." },
];

const TECHNIQUES: { icon: IconName; title: string; does: string; helps: string }[] = [
  {
    icon: "pipeline",
    title: "Điều phối agent có trạng thái",
    does: "Các bước của agent được nối thành một đồ thị bằng LangGraph. Trạng thái được lưu lại (checkpoint) sau mỗi bước, và quy trình dừng ở những chỗ cần người quyết định.",
    helps: "Người dùng trả lời sau vài phút hay vài giờ thì lần chạy vẫn đi tiếp đúng chỗ, không làm lại từ đầu.",
  },
  {
    icon: "tests",
    title: "Sinh pipeline và test tách biệt",
    does: "Agent viết code sinh model dbt và DAG Airflow. Một agent khác viết test chỉ dựa trên yêu cầu đã duyệt, không xem code của bước trước.",
    helps: "Viết test độc lập giúp giảm nguy cơ lặp lại lỗi của bước sinh code và tăng cơ hội phát hiện sai lệch.",
  },
  {
    icon: "sandbox",
    title: "Kiểm chứng SQL và chạy thử trong sandbox",
    does: "sqlglot đọc từng câu SQL để chặn lệnh nguy hiểm và tên bảng, cột không có thật. dbt chạy trong DuckDB cục bộ có giới hạn thời gian và bộ nhớ, rồi đối soát số liệu.",
    helps: "Kết luận đạt hay lỗi đến từ phép đo bằng code, không dựa vào lời AI tự báo “đã xong”.",
  },
  {
    icon: "optimize",
    title: "Tối ưu có đo lường",
    does: "Thử lần lượt luật cố định, sqlglot, rồi mới đến AI. Bản mới chỉ được dùng khi kết quả giống hệt trên 6 bộ dữ liệu thử và nhanh hơn ngưỡng đặt trước. Chạy lại trên sandbox mà lệch thì khôi phục bản gốc.",
    helps: "Truy vấn nhanh hơn mà không đổi kết quả. Không đáng tối ưu thì giữ nguyên và ghi lý do.",
  },
  {
    icon: "drift",
    title: "Phát hiện thay đổi cấu trúc nguồn",
    does: "So cấu trúc nguồn với lần trước để thấy cột bị đổi kiểu, đổi tên hoặc bị xóa, và chỉ ra pipeline bị ảnh hưởng. Khi người dùng yêu cầu, hệ thống đề xuất bản vá; bản vá vẫn phải qua duyệt.",
    helps: "Thay đổi gây hỏng được chặn sớm và hiện rõ, thay vì làm số liệu sai mà không ai hay.",
  },
  {
    icon: "password",
    title: "Phân quyền nguồn, dữ liệu vào prompt và ngân sách AI",
    does: "Người dùng chỉ thấy nguồn của phòng mình. Mỗi nguồn có mức dữ liệu AI được xem: chỉ cấu trúc, thêm thống kê, hoặc vài dòng đã che. Lỗi được che giá trị trước khi gửi cho AI. Mỗi người có trần chi phí gọi AI mỗi ngày.",
    helps: "Giảm rủi ro lộ dữ liệu cho AI và giữ chi phí trong giới hạn đã đặt.",
  },
];

const TECH_IN_APP: { role: string; icon: IconName; items: { name: string; text: string }[] }[] = [
  {
    role: "Giao diện",
    icon: "system",
    items: [
      { name: "Next.js, React, TypeScript", text: "Dựng trang web bạn đang xem." },
      { name: "Monaco Editor", text: "Khung xem code và so sánh thay đổi ngay trên web." },
    ],
  },
  {
    role: "API và điều phối",
    icon: "agent",
    items: [
      { name: "FastAPI", text: "Máy chủ nhận yêu cầu từ web và chạy agent ở nền." },
      { name: "LangGraph", text: "Xếp các bước của agent thành quy trình có điểm dừng chờ người." },
      { name: "Pydantic", text: "Khuôn dữ liệu cố định giữa các bước; sai trường hay kiểu thì báo ngay." },
    ],
  },
  {
    role: "Xử lý và kiểm chứng",
    icon: "sandbox",
    items: [
      { name: "dbt", text: "Chạy và kiểm thử các model SQL do agent viết." },
      { name: "DuckDB", text: "Cơ sở dữ liệu cục bộ dùng làm sandbox chạy thử." },
      { name: "sqlglot", text: "Đọc và phân tích SQL để kiểm tra an toàn và tìm cách viết nhanh hơn." },
    ],
  },
  {
    role: "Lưu trữ",
    icon: "sources",
    items: [
      {
        name: "PostgreSQL",
        text: "Lưu tài khoản và sổ nguồn; khi triển khai còn lưu lần chạy, sổ lỗi và trạng thái agent.",
      },
      { name: "SQLite", text: "Lựa chọn mặc định khi chạy thử trên máy, thay PostgreSQL cho phần lần chạy." },
    ],
  },
];

const TECH_OUTPUT = [
  { name: "Model dbt", text: "Các file SQL làm sạch dữ liệu nguồn và tính ra bảng kết quả." },
  { name: "Test dbt", text: "Kiểm tra khóa không trùng, kiểu dữ liệu đọc được và số liệu khớp nguồn." },
  {
    name: "DAG Airflow",
    text: "File Python lên lịch chạy pipeline. Hệ thống kiểm tra file này bằng code nhưng không chạy Airflow; DAG chạy trên Airflow của bạn sau khi bàn giao.",
  },
];

const ROADMAP: { title: string; text: string }[] = [
  {
    title: "Đánh giá thêm bằng LLM thật",
    text: "Đo trên nhiều tình huống và dữ liệu thực tế hơn. Nhiều phép đo hiện mới chạy ở chế độ mô phỏng, trên dữ liệu giả lập.",
  },
  {
    title: "Mở rộng nguồn kết nối và nạp dữ liệu tăng dần",
    text: "Hiện đọc được tệp, DuckDB và PostgreSQL chỉ đọc. Nạp phần mới (incremental) mới dừng ở mức cấu hình, chưa sinh trọn vào model.",
  },
  {
    title: "Hoàn thiện triển khai, giám sát và phục hồi",
    text: "Đưa hệ thống lên môi trường vận hành, theo dõi tình trạng và xử lý khi một lần chạy bị gián đoạn.",
  },
  {
    title: "Thu thập phản hồi người dùng",
    text: "Lắng nghe người dùng thử để cải thiện trải nghiệm tạo và duyệt pipeline.",
  },
];

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

function DemoButton({ label = "Trải nghiệm demo" }: { label?: string }) {
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
    <header className="docs-section-head">
      <p className="docs-kicker">{kicker}</p>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </header>
  );
}

export default function DocsPage() {
  return (
    <div className="docs-page">
      <a href="#tong-quan" className="skip-link">
        Bỏ qua tới nội dung
      </a>
      <header className="docs-top">
        <div className="docs-container docs-top-inner">
          <Link href="/" className="docs-brand">
            <SparkIcon size={22} className="brand-spark" />
            <span>
              P-113<span className="docs-brand-more"> Agent Studio</span>
            </span>
          </Link>
          <nav className="docs-top-links" aria-label="Liên kết nhanh">
            <Link href="/login" className="btn docs-top-btn">
              Đăng nhập
            </Link>
            <DocsThemeToggle />
          </nav>
        </div>
      </header>

      <DocsSectionNav items={SECTIONS} />

      <main className="docs-main" id="main">
        <section id="tong-quan" className="docs-section docs-overview" aria-labelledby="tong-quan-title">
          <div className="docs-container docs-hero">
            <div className="docs-hero-text">
              <p className="docs-kicker">Giới thiệu dự án P-113 · bản demo nghiên cứu</p>
              <h1 id="tong-quan-title">Từ yêu cầu bằng lời đến pipeline dữ liệu có kiểm chứng</h1>
              <p className="docs-lead">
                Bạn mô tả bảng số liệu cần có. AI làm rõ yêu cầu, đề xuất kế hoạch, viết code và chạy thử trên bản sao
                dữ liệu. Các phép đo bằng code cho bạn bằng chứng để xem và duyệt trước khi sử dụng.
              </p>
              <div className="docs-actions">
                <DemoButton />
                <a href="#quy-trinh" className="btn">
                  Xem quy trình
                </a>
              </div>
              <p className="docs-note">
                <Icon name="info" size={16} /> Không cần tài khoản. Demo dùng dữ liệu mẫu dựng sẵn, không gọi AI thật.
              </p>
            </div>
            <figure className="docs-hero-shot">
              <Shot
                name="run"
                alt="Màn một lần chạy: thanh điều hướng, tiến trình bốn giai đoạn đã xong và danh sách bước kiểm chứng"
                width={1244}
                height={760}
                sizes="(max-width: 960px) 100vw, 700px"
              />
              <figcaption>Màn một lần chạy trong chế độ khách. Dữ liệu mẫu.</figcaption>
            </figure>
          </div>
          <div className="docs-container">
            <dl className="docs-columns">
              {OVERVIEW.map((item) => (
                <div key={item.title}>
                  <dt>{item.title}</dt>
                  <dd>{item.text}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section id="demo" className="docs-section" aria-labelledby="demo-title">
          <div className="docs-container">
            <SectionHead id="demo" kicker="Demo" title="Gộp dữ liệu bán hàng thành báo cáo doanh thu">
              <p className="docs-intro">
                Một cửa hàng bán trên hai sàn thương mại điện tử và website riêng. Mỗi nơi xuất đơn hàng theo một kiểu:
                có đơn bị ghi trùng, ngày viết lẫn nhiều định dạng, số tiền có chỗ ghi “1.075.000”.
              </p>
            </SectionHead>
            <div className="docs-split">
              <div>
                <blockquote className="docs-request">
                  <span>Câu yêu cầu mẫu</span>
                  “Gộp đơn hàng từ ba nguồn, tính doanh thu theo ngày.”
                </blockquote>
                <h3>Trong demo, bạn có thể</h3>
                <ul className="docs-points">
                  {DEMO_POINTS.map((point) => (
                    <li key={point.text}>
                      <Icon name={point.icon} size={20} />
                      <span>{point.text}</span>
                    </li>
                  ))}
                </ul>
                <p className="docs-muted">
                  Trong khung Yêu cầu mới, nút “Thử ngay với ví dụ” điền sẵn câu trên. Kết quả là mẫu dựng sẵn, các thao
                  tác duyệt chỉ là giả lập.
                </p>
                <DemoButton label="Mở demo" />
              </div>
              <figure className="docs-figure">
                <Shot
                  name="review"
                  alt="Màn duyệt: cột bằng chứng do code đo đặt cạnh cột lời AI chưa kiểm chứng, bên dưới là khung quyết định"
                  width={1244}
                  height={720}
                  sizes="(max-width: 960px) 100vw, 640px"
                />
                <figcaption>Màn duyệt: “Code đo” tách khỏi “LLM nói”. Dữ liệu mẫu.</figcaption>
              </figure>
            </div>
          </div>
        </section>

        <section id="quy-trinh" className="docs-section" aria-labelledby="quy-trinh-title">
          <div className="docs-container">
            <SectionHead id="quy-trinh" kicker="Quy trình" title="Năm bước từ câu chữ đến pipeline được duyệt" />
            <ol className="docs-flow">
              {FLOW.map((step, index) => (
                <li key={step.title}>
                  <span className="docs-flow-num" aria-hidden="true">
                    {index + 1}
                  </span>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                  <p className="docs-actors">
                    <span className="sr-only">Ai làm: </span>
                    {step.actors.map((actor) => (
                      <span key={actor} className="docs-actor" data-actor={actor}>
                        {ACTOR_TEXT[actor]}
                      </span>
                    ))}
                  </p>
                </li>
              ))}
            </ol>

            <div className="docs-principle">
              <div>
                <h3>Con người quyết định. AI thực thi. Code kiểm chứng.</h3>
                <p className="docs-muted">
                  AI đề xuất cách làm; các phép kiểm tra bằng code cung cấp bằng chứng để người dùng đánh giá.
                </p>
              </div>
              <ul>
                {PRINCIPLE.map((item) => (
                  <li key={item.actor} data-actor={item.actor}>
                    <strong>{item.title}</strong>
                    <span>{item.text}</span>
                  </li>
                ))}
              </ul>
            </div>

            <p className="docs-callout">
              <Icon name="info" size={18} />
              <span>
                Hệ thống không tự đưa pipeline lên môi trường thật. Với lần chạy thật, người dùng tải gói code (.zip)
                về, đưa vào kho mã của mình và chỉ triển khai sau khi Reviewer duyệt, theo quy trình riêng bên ngoài hệ
                thống.
              </span>
            </p>
          </div>
        </section>

        <section id="ky-thuat" className="docs-section" aria-labelledby="ky-thuat-title">
          <div className="docs-container">
            <SectionHead id="ky-thuat" kicker="Kỹ thuật" title="Những gì đứng sau mỗi bước" />
            <ul className="docs-features">
              {TECHNIQUES.map((item) => (
                <li key={item.title}>
                  <Icon name={item.icon} size={22} className="docs-feature-icon" />
                  <h3>{item.title}</h3>
                  <p>{item.does}</p>
                  <p className="docs-feature-help">
                    <strong>Có ích gì:</strong> {item.helps}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="cong-nghe" className="docs-section" aria-labelledby="cong-nghe-title">
          <div className="docs-container">
            <SectionHead id="cong-nghe" kicker="Công nghệ" title="Ứng dụng được xây bằng gì" />
            <div className="docs-tech-groups">
              {TECH_IN_APP.map((group) => (
                <div key={group.role}>
                  <h3>
                    <Icon name={group.icon} size={18} /> {group.role}
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
            <div className="docs-output">
              <h3>
                <Icon name="file" size={18} /> Đầu ra: các file agent viết để bạn mang đi dùng
              </h3>
              <dl className="docs-tech docs-tech-row">
                {TECH_OUTPUT.map((item) => (
                  <div key={item.name}>
                    <dt>{item.name}</dt>
                    <dd>{item.text}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        <section id="huong-di" className="docs-section" aria-labelledby="huong-di-title">
          <div className="docs-container">
            <SectionHead id="huong-di" kicker="Hướng đi" title="Những việc dự định làm tiếp">
              <p className="docs-intro">Đây là định hướng, chưa phải tính năng đã có và chưa gắn thời hạn.</p>
            </SectionHead>
            <ol className="docs-roadmap">
              {ROADMAP.map((item) => (
                <li key={item.title}>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </li>
              ))}
            </ol>
            <div className="docs-end">
              <p>
                Đây là bản demo nghiên cứu. Chế độ khách mô phỏng quy trình bằng dữ liệu mẫu; hệ thống không tự triển
                khai pipeline lên môi trường thật.
              </p>
              <DemoButton />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
