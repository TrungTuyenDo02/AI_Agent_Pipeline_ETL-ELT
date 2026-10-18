// Chữ của trang "Giới thiệu dự án" (/docs). Mỗi đoạn tối đa 2 dòng; `**…**` là ý chính (in đậm, xem components/docs/Rich.tsx).
// Viết cho người xem lần đầu: câu ngắn, không nêu địa chỉ API, cấu hình, số đo hay thông tin nội bộ.
// Mỗi mô tả phải có căn cứ trong code; phân biệt rõ tính năng hiện có, chế độ khách (mô phỏng) và định hướng.

import type { IconName } from "@/lib/icons";

export type Actor = "human" | "ai" | "code";
/** Màu nhấn riêng của từng thẻ (biến trong styles/tokens.css). */
export type Tone = "primary" | "ai" | "ok" | "highlight" | "guide" | "warn";

export const LANDING = {
  meta: {
    title: "Giới thiệu dự án · PipeSmith",
    description:
      "PipeSmith hỗ trợ xây dựng và tối ưu pipeline dữ liệu: làm rõ yêu cầu, lập kế hoạch, sinh code, chạy thử và để người dùng duyệt.",
  },
  skip: "Bỏ qua tới nội dung",
  quickLinks: "Liên kết nhanh",
  login: "Đăng nhập",
  sections: [
    { id: "tong-quan", label: "Tổng quan" },
    { id: "cach-hoat-dong", label: "Cách hoạt động" },
    { id: "demo", label: "Demo" },
    { id: "quy-trinh", label: "Quy trình" },
    { id: "ky-thuat", label: "Kỹ thuật" },
    { id: "cong-nghe", label: "Công nghệ" },
    { id: "huong-di", label: "Hướng đi" },
  ],
  hero: {
    kicker: "PipeSmith · Dự án P-113 · Bản demo nghiên cứu",
    title: "Từ một câu yêu cầu đến pipeline dữ liệu có kiểm chứng",
    lead: "Bạn mô tả bảng số liệu cần có. **AI viết pipeline, code chạy thử và đo**, bạn xem bằng chứng rồi mới duyệt.",
    cta: "Trải nghiệm demo",
    secondary: "Xem quy trình",
    note: "Không cần tài khoản. Demo dùng **dữ liệu mẫu dựng sẵn**, không gọi AI thật.",
    shotAlt: "Màn một lần chạy: thanh điều hướng, tiến trình bốn giai đoạn đã xong và danh sách bước kiểm chứng",
    shotCaption: "Màn một lần chạy trong chế độ khách. Dữ liệu mẫu.",
  },
  overview: [
    {
      icon: "warning",
      tone: "highlight",
      title: "Bài toán",
      text: "Dữ liệu nằm ở nhiều nguồn, mỗi nơi ghi một kiểu. **Viết pipeline bằng tay tốn thời gian và dễ sai.**",
    },
    {
      icon: "agent",
      tone: "primary",
      title: "P-113 làm gì",
      text: "**AI viết pipeline** lấy, làm sạch và tính ra bảng số liệu; **code chạy thử và đo** kết quả.",
    },
    {
      icon: "sandbox",
      tone: "ok",
      title: "Điều hệ thống không làm",
      text: "**Không chạy trên dữ liệu thật đang vận hành**, không tự triển khai. Bạn duyệt rồi tự đưa code đi.",
    },
  ] satisfies { icon: IconName; tone: Tone; title: string; text: string }[],
  how: {
    kicker: "Cách hoạt động",
    title: "Bốn bước, mỗi bước có người hoặc code kiểm",
    steps: [
      { icon: "create", tone: "primary", title: "Yêu cầu", text: "Bạn viết **một câu** về bảng số liệu cần có." },
      { icon: "code", tone: "ai", title: "Sinh code", text: "AI viết **model dbt, DAG Airflow và test**." },
      { icon: "sandbox", tone: "ok", title: "Chạy thử", text: "Code chạy **trong sandbox DuckDB** và đo kết quả." },
      { icon: "approve", tone: "warn", title: "Duyệt", text: "Reviewer **xem diff và bằng chứng** rồi mới duyệt." },
    ] satisfies { icon: IconName; tone: Tone; title: string; text: string }[],
  },
  demo: {
    kicker: "Demo",
    title: "Gộp dữ liệu bán hàng thành báo cáo doanh thu",
    intro: "Cửa hàng bán trên hai sàn và website riêng. **Đơn ghi trùng, ngày lẫn định dạng, tiền ghi “1.075.000”.**",
    requestLabel: "Câu yêu cầu mẫu",
    request: "“Gộp đơn hàng từ ba nguồn, tính doanh thu theo ngày.”",
    pointsTitle: "Trong demo, bạn có thể",
    // Khớp kịch bản chế độ khách (lib/demo/fixtures.ts). Chỉ nêu điều riêng của demo; các bước chung nằm ở "Quy trình".
    points: [
      { icon: "info", text: "Trả lời **hai câu hỏi trắc nghiệm** về đơn được tính doanh thu và cách xử lý đơn trùng." },
      { icon: "runs", text: "Mở **các lần chạy mẫu**: đang chạy, chờ duyệt, đã dừng và đã duyệt." },
      {
        icon: "reviewer",
        text: "Đổi vai sang **Reviewer** để xem diff, bằng chứng do code đo và bấm Duyệt (giả lập).",
      },
    ] satisfies { icon: IconName; text: string }[],
    note: "Nút “Thử ngay với ví dụ” điền sẵn câu trên. **Kết quả là mẫu dựng sẵn**, thao tác duyệt chỉ là giả lập.",
    cta: "Mở demo",
    shotAlt: "Màn duyệt: cột bằng chứng do code đo đặt cạnh cột lời AI chưa kiểm chứng, bên dưới là khung quyết định",
    shotCaption: "Màn duyệt: “Code đo” tách khỏi “LLM nói”. Dữ liệu mẫu.",
  },
  flow: {
    kicker: "Quy trình",
    title: "Năm bước từ câu chữ đến pipeline được duyệt",
    actorsLabel: "Ai làm: ",
    actors: { human: "Con người", ai: "AI", code: "Code" } satisfies Record<Actor, string>,
    steps: [
      {
        title: "Mô tả yêu cầu",
        text: "Bạn viết một câu về bảng số liệu cần có. **Code lọc trước** câu rỗng, vô nghĩa hoặc lạc đề.",
        actors: ["human", "code"],
      },
      {
        title: "Làm rõ, duyệt kế hoạch",
        text: "AI hỏi lại chỗ chưa rõ, đề xuất nguồn, cách làm sạch và cột kết quả. **Bạn đồng ý mới viết code.**",
        actors: ["ai", "human"],
      },
      {
        title: "Sinh code và test",
        text: "AI viết model dbt, DAG Airflow và test. **Agent viết test làm riêng**, không xem code pipeline.",
        actors: ["ai"],
      },
      {
        title: "Chạy thử, kiểm tra, tối ưu",
        text: "Code chạy trong **sandbox, bản sao dữ liệu tách riêng**. Máy đối soát số liệu rồi thử truy vấn nhanh hơn.",
        actors: ["code", "ai"],
      },
      {
        title: "Người dùng duyệt",
        text: "Reviewer xem diff và bằng chứng, rồi **duyệt hoặc yêu cầu sửa** kèm ghi chú.",
        actors: ["human"],
      },
    ] satisfies { title: string; text: string; actors: Actor[] }[],
    principleTitle: "Con người quyết định. AI thực thi. Code kiểm chứng.",
    principleText: "AI đề xuất cách làm; **phép kiểm tra bằng code** cho người dùng bằng chứng để đánh giá.",
    principle: [
      { actor: "human", title: "Con người quyết định", text: "Trả lời câu hỏi, duyệt kế hoạch, duyệt code." },
      { actor: "ai", title: "AI thực thi", text: "Hỏi lại, lập kế hoạch, viết code và test." },
      { actor: "code", title: "Code kiểm chứng", text: "Chạy thử, đo kết quả, so trước và sau. Không nhờ AI tự chấm." },
    ] satisfies { actor: Actor; title: string; text: string }[],
    callout:
      "**Hệ thống không tự đưa pipeline lên môi trường thật.** Bạn tải gói code (.zip) và chỉ triển khai sau khi Reviewer duyệt.",
  },
  techniques: {
    kicker: "Kỹ thuật",
    title: "Những gì đứng sau mỗi bước",
    helpsLabel: "Có ích gì:",
    items: [
      {
        icon: "pipeline",
        tone: "primary",
        title: "Điều phối agent có trạng thái",
        does: "LangGraph nối các bước; **trạng thái lưu sau mỗi bước**, quy trình dừng ở chỗ cần người.",
        helps: "Trả lời sau vài giờ vẫn chạy tiếp đúng chỗ.",
      },
      {
        icon: "tests",
        tone: "ai",
        title: "Sinh pipeline và test tách biệt",
        does: "Một agent viết dbt và Airflow; **agent khác viết test** chỉ dựa trên yêu cầu đã duyệt.",
        helps: "Giảm nguy cơ lặp lại lỗi của bước sinh code.",
      },
      {
        icon: "sandbox",
        tone: "ok",
        title: "Kiểm chứng SQL, chạy thử trong sandbox",
        does: "sqlglot **chặn lệnh nguy hiểm và tên bảng, cột bịa**; dbt chạy trong DuckDB có giới hạn.",
        helps: "Đạt hay lỗi do code đo, không do AI tự báo.",
      },
      {
        icon: "optimize",
        tone: "highlight",
        title: "Tối ưu có đo lường",
        does: "Luật cố định → sqlglot → AI. **Chỉ dùng bản mới khi kết quả giống hệt** trên 6 bộ dữ liệu thử.",
        helps: "Nhanh hơn mà không đổi kết quả; không đáng thì giữ nguyên.",
      },
      {
        icon: "drift",
        tone: "guide",
        title: "Phát hiện thay đổi cấu trúc nguồn",
        does: "So cấu trúc nguồn với lần trước, **chỉ ra pipeline bị ảnh hưởng**; bản vá vẫn phải qua duyệt.",
        helps: "Chặn sớm, không để số liệu sai mà không ai hay.",
      },
      {
        icon: "password",
        tone: "warn",
        title: "Phân quyền nguồn, dữ liệu vào prompt, ngân sách AI",
        does: "Mỗi nguồn có **mức dữ liệu AI được xem**; lỗi được che giá trị trước khi gửi cho AI.",
        helps: "Giảm rủi ro lộ dữ liệu, giữ chi phí AI trong hạn mức mỗi ngày.",
      },
    ] satisfies { icon: IconName; tone: Tone; title: string; does: string; helps: string }[],
  },
  tech: {
    kicker: "Công nghệ",
    title: "Ứng dụng được xây bằng gì",
    groups: [
      {
        role: "Giao diện",
        icon: "system",
        tone: "primary",
        items: [
          { name: "Next.js, React, TypeScript", text: "Dựng trang web bạn đang xem." },
          { name: "Monaco Editor", text: "Khung xem code và so sánh thay đổi ngay trên web." },
        ],
      },
      {
        role: "API và điều phối",
        icon: "agent",
        tone: "ai",
        items: [
          { name: "FastAPI", text: "Máy chủ nhận yêu cầu từ web và chạy agent ở nền." },
          { name: "LangGraph", text: "Xếp các bước của agent thành quy trình có điểm dừng chờ người." },
          { name: "Pydantic", text: "Khuôn dữ liệu cố định giữa các bước; sai trường hay kiểu thì báo ngay." },
        ],
      },
      {
        role: "Xử lý và kiểm chứng",
        icon: "sandbox",
        tone: "ok",
        items: [
          { name: "dbt", text: "Chạy và kiểm thử các model SQL do agent viết." },
          { name: "DuckDB", text: "Cơ sở dữ liệu cục bộ dùng làm sandbox chạy thử." },
          { name: "sqlglot", text: "Đọc và phân tích SQL để kiểm tra an toàn và tìm cách viết nhanh hơn." },
        ],
      },
      {
        role: "Lưu trữ",
        icon: "sources",
        tone: "highlight",
        items: [
          {
            name: "PostgreSQL",
            text: "Lưu tài khoản, sổ nguồn; khi triển khai còn lưu lần chạy, sổ lỗi, trạng thái agent.",
          },
          { name: "SQLite", text: "Mặc định khi chạy thử trên máy, thay PostgreSQL cho phần lần chạy." },
        ],
      },
    ] satisfies { role: string; icon: IconName; tone: Tone; items: { name: string; text: string }[] }[],
    outputTitle: "Đầu ra: các file agent viết để bạn mang đi dùng",
    output: [
      { name: "Model dbt", text: "Các file SQL làm sạch dữ liệu nguồn và tính ra bảng kết quả." },
      { name: "Test dbt", text: "Kiểm tra khóa không trùng, kiểu dữ liệu đọc được và số liệu khớp nguồn." },
      {
        name: "DAG Airflow",
        text: "File Python lên lịch chạy. **Hệ thống kiểm tra bằng code, không chạy Airflow**; DAG chạy trên Airflow của bạn.",
      },
    ],
  },
  roadmap: {
    kicker: "Hướng đi",
    title: "Những việc dự định làm tiếp",
    intro: "Đây là **định hướng**, chưa phải tính năng đã có và chưa gắn thời hạn.",
    items: [
      {
        title: "Đánh giá thêm bằng LLM thật",
        text: "Đo trên nhiều tình huống thực tế hơn. **Nhiều phép đo hiện mới chạy mô phỏng**, trên dữ liệu giả lập.",
      },
      {
        title: "Mở rộng nguồn kết nối, nạp dữ liệu tăng dần",
        text: "Hiện đọc tệp, DuckDB và PostgreSQL chỉ đọc. **Nạp phần mới (incremental) mới ở mức cấu hình.**",
      },
      {
        title: "Hoàn thiện triển khai, giám sát và phục hồi",
        text: "Đưa lên môi trường vận hành, **theo dõi và xử lý khi một lần chạy bị gián đoạn**.",
      },
      {
        title: "Thu thập phản hồi người dùng",
        text: "Lắng nghe người dùng thử để **cải thiện việc tạo và duyệt pipeline**.",
      },
    ],
  },
  end: {
    title: "Xem tận mắt trong vài phút",
    text: "Đây là bản demo nghiên cứu. **Chế độ khách dùng dữ liệu mẫu**; hệ thống không tự triển khai lên môi trường thật.",
    cta: "Trải nghiệm demo",
  },
};
