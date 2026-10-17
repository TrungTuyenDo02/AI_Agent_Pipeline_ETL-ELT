// Chữ của trang đăng nhập, hai ngôn ngữ (CLAUDE.md 9.2: giao diện chính là tiếng Việt; EN chỉ dành cho trang giới thiệu/đăng nhập).

export type Lang = "vi" | "en";
export const LANG_KEY = "p113.lang";

export type FlowKind = "agent" | "code" | "human";

export interface LoginText {
  welcome: string;
  welcomeAccent: string;
  sub: string;
  user: string;
  userError: string;
  password: string;
  passwordError: string;
  showPassword: string;
  hidePassword: string;
  remember: string;
  submit: string;
  submitting: string;
  forgot: string;
  forgotAction: string;
  guestTry: string;
  guestHint: string;
  docs: string;
  contactText: string;
  contactMail: string;
  heroTitle: string;
  heroSub: string;
  quote: string;
  canvasLabel: string;
  flowLabel: string;
  flow: { code: string; label: string; kind: FlowKind; hint: string }[];
  legendLabel: string;
  legend: { kind: FlowKind; label: string }[];
  toolsLabel: string;
  tools: string[];
  statsLabel: string;
  highlights: { value: string; label: string; hint: string }[];
  accountsTitle: string;
  accountsHint: string;
  roles: { engineer: string; reviewer: string; admin: string };
  footer: string;
  langLabel: string;
  themeToLight: string;
  themeToDark: string;
}

export const LOGIN_TEXT: Record<Lang, LoginText> = {
  vi: {
    welcome: "CHÀO MỪNG",
    welcomeAccent: "TRỞ LẠI",
    sub: "Đăng nhập bằng tài khoản được cấp để tiếp tục",
    user: "Tên đăng nhập",
    userError: "Nhập tên đăng nhập.",
    password: "Mật khẩu",
    passwordError: "Nhập mật khẩu.",
    showPassword: "Hiện mật khẩu",
    hidePassword: "Ẩn mật khẩu",
    remember: "Ghi nhớ tên đăng nhập trên máy này",
    submit: "Đăng nhập",
    submitting: "Đang đăng nhập…",
    forgot: "Quên mật khẩu?",
    forgotAction: "Liên hệ quản trị viên",
    guestTry: "Dùng thử với dữ liệu mẫu",
    docs: "Tài liệu",
    guestHint: "Không cần tài khoản. Kết quả là mẫu dựng sẵn, không do AI chạy thật.",
    contactText:
      "Tài khoản do quản trị viên của công ty cấp, không tự đăng ký. Gửi cho quản trị viên tên đăng nhập và vai trò cần dùng (Engineer hoặc Reviewer); họ sẽ cấp hoặc đặt lại mật khẩu cho bạn.",
    contactMail: "Gửi email cho quản trị viên",
    heroTitle: "Từ một câu yêu cầu đến pipeline đã chạy thử.",
    heroSub: "Lập kế hoạch, sinh dbt và Airflow, chạy thử trong sandbox. Người duyệt xem bằng chứng rồi mới merge.",
    quote: "“Agent chỉ thấy cấu trúc và thống kê, không bao giờ thấy dòng dữ liệu thật.”",
    canvasLabel: "Tổng quan dự án",
    flowLabel: "Luồng làm việc",
    flow: [
      {
        code: "G0",
        label: "Cổng vào",
        kind: "code",
        hint: "Chặn câu vô nghĩa, lạc đề hoặc tấn công prompt trước khi tốn token.",
      },
      {
        code: "G1",
        label: "Cấu trúc nguồn",
        kind: "code",
        hint: "Nguồn đổi kiểu, đổi tên hoặc xóa cột thì chặn và báo rõ.",
      },
      { code: "E1", label: "Kế hoạch", kind: "agent", hint: "Agent lập kế hoạch, hỏi lại khi chưa rõ." },
      {
        code: "J1b",
        label: "Duyệt kế hoạch",
        kind: "human",
        hint: "Người duyệt kế hoạch và chọn cách nạp, lịch chạy.",
      },
      { code: "E3", label: "Sinh code", kind: "agent", hint: "Agent viết model dbt, DAG Airflow và test." },
      { code: "V1", label: "An toàn", kind: "code", hint: "Code thuần chặn SQL nguy hiểm và tên bảng, cột bịa." },
      { code: "V2", label: "Chạy thử", kind: "code", hint: "dbt build và test thật trong sandbox DuckDB." },
      { code: "E4", label: "Tối ưu", kind: "agent", hint: "Chỉ áp dụng khi kết quả giống hệt và nhanh hơn." },
      { code: "J2", label: "Duyệt cuối", kind: "human", hint: "Người duyệt xem bằng chứng đo được rồi mới merge." },
    ],
    legendLabel: "Ai làm bước nào",
    legend: [
      { kind: "agent", label: "Agent làm" },
      { kind: "code", label: "Code kiểm" },
      { kind: "human", label: "Người quyết" },
    ],
    toolsLabel: "Công cụ",
    tools: ["LangGraph", "dbt", "DuckDB", "Airflow", "sqlglot", "FastAPI", "Next.js", "PostgreSQL"],
    statsLabel: "Số đo được",
    highlights: [
      {
        value: "0",
        label: "dòng dữ liệu thật tới AI",
        hint: "AI chỉ thấy cấu trúc, thống kê và dạng giá trị, qua một cửa duy nhất.",
      },
      {
        value: "14/15",
        label: "lỗi giả bị chặn",
        hint: "Mutation test: cố ý sửa sai pipeline, bộ kiểm chứng phải bắt được.",
      },
      {
        value: "0/6",
        label: "ca đổi nguồn sai mà báo đạt",
        hint: "Mô phỏng 6 kiểu backend đổi nguồn không báo trước.",
      },
      {
        value: "0 token",
        label: "vá khi nguồn đổi tên cột",
        hint: "Bản vá nhanh sửa bằng code và dùng lại kế hoạch đã duyệt.",
      },
    ],
    accountsTitle: "Tài khoản demo",
    accountsHint: "Bấm để điền sẵn. Mật khẩu cố định, chỉ dùng cho máy demo.",
    roles: { engineer: "Engineer", reviewer: "Reviewer", admin: "Admin" },
    footer: "© 2026 P-113 Agent Studio · Phần mềm nội bộ, tài khoản do quản trị viên cấp.",
    langLabel: "Ngôn ngữ",
    themeToLight: "Chuyển sang giao diện sáng",
    themeToDark: "Chuyển sang giao diện tối",
  },
  en: {
    welcome: "WELCOME",
    welcomeAccent: "BACK",
    sub: "Sign in with your issued account to continue",
    user: "Username",
    userError: "Enter your username.",
    password: "Password",
    passwordError: "Enter your password.",
    showPassword: "Show password",
    hidePassword: "Hide password",
    remember: "Remember my username on this device",
    submit: "Sign in",
    submitting: "Signing in…",
    forgot: "Forgot password?",
    forgotAction: "Contact your administrator",
    guestTry: "Try it with sample data",
    docs: "Docs",
    guestHint: "No account needed. Results are prebuilt samples, not produced by a live AI run.",
    contactText:
      "Accounts are issued by your company administrator; there is no self-signup. Send them your username and the role you need (Engineer or Reviewer) and they will issue or reset your password.",
    contactMail: "Email the administrator",
    heroTitle: "From one sentence to a pipeline that already ran.",
    heroSub:
      "Plans the work, generates dbt and Airflow, runs it in a sandbox. A reviewer checks the evidence before any merge.",
    quote: "“The agent sees structure and statistics, never real data rows.”",
    canvasLabel: "Project overview",
    flowLabel: "Workflow",
    flow: [
      {
        code: "G0",
        label: "Input gate",
        kind: "code",
        hint: "Blocks nonsense, off-topic or prompt attacks before any token is spent.",
      },
      {
        code: "G1",
        label: "Source schema",
        kind: "code",
        hint: "Blocks the run and explains it when a source changes type, name or drops a column.",
      },
      { code: "E1", label: "Plan", kind: "agent", hint: "The agent plans and asks when something is unclear." },
      {
        code: "J1b",
        label: "Approve plan",
        kind: "human",
        hint: "A person approves the plan and picks load mode and schedule.",
      },
      { code: "E3", label: "Generate", kind: "agent", hint: "The agent writes dbt models, Airflow DAGs and tests." },
      {
        code: "V1",
        label: "Safety",
        kind: "code",
        hint: "Plain code blocks unsafe SQL and invented tables or columns.",
      },
      { code: "V2", label: "Run", kind: "code", hint: "Real dbt build and tests in a DuckDB sandbox." },
      { code: "E4", label: "Optimise", kind: "agent", hint: "Applied only when results are identical and faster." },
      {
        code: "J2",
        label: "Final review",
        kind: "human",
        hint: "A reviewer checks the measured evidence before merging.",
      },
    ],
    legendLabel: "Who does each step",
    legend: [
      { kind: "agent", label: "Agent works" },
      { kind: "code", label: "Code checks" },
      { kind: "human", label: "Human decides" },
    ],
    toolsLabel: "Tools",
    tools: ["LangGraph", "dbt", "DuckDB", "Airflow", "sqlglot", "FastAPI", "Next.js", "PostgreSQL"],
    statsLabel: "Measured numbers",
    highlights: [
      {
        value: "0",
        label: "real data rows reach the AI",
        hint: "The AI sees structure, statistics and value shapes through a single gate.",
      },
      {
        value: "14/15",
        label: "seeded bugs caught",
        hint: "Mutation test: pipelines are broken on purpose and the checks must catch it.",
      },
      {
        value: "0/6",
        label: "source changes wrong but green",
        hint: "Six ways a backend can change a source without telling anyone, simulated.",
      },
      {
        value: "0 tokens",
        label: "to patch a renamed column",
        hint: "The fast patch fixes it with code and reuses the approved plan.",
      },
    ],
    accountsTitle: "Demo accounts",
    accountsHint: "Click to fill in. Fixed passwords, for demo machines only.",
    roles: { engineer: "Engineer", reviewer: "Reviewer", admin: "Admin" },
    footer: "© 2026 P-113 Agent Studio · Internal software, accounts issued by an administrator.",
    langLabel: "Language",
    themeToLight: "Switch to light theme",
    themeToDark: "Switch to dark theme",
  },
};

/** Tài khoản demo: chỉ hiện khi build với NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS=true (demo/run_demo.py đặt sẵn). Khớp demo/README.md. */
export const DEMO_ACCOUNTS: { user: string; password: string; role: keyof LoginText["roles"] }[] = [
  { user: "an", password: "Demo-Engineer-2026", role: "engineer" },
  { user: "binh", password: "Demo-Reviewer-2026", role: "reviewer" },
  { user: "quantri", password: "Demo-Admin-2026", role: "admin" },
];
export const SHOW_DEMO_ACCOUNTS = process.env.NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS === "true";
/** Email quản trị viên (công khai, tùy chọn): đặt NEXT_PUBLIC_ADMIN_CONTACT khi build thì nút Liên hệ có thêm liên kết gửi email. */
export const ADMIN_CONTACT = (process.env.NEXT_PUBLIC_ADMIN_CONTACT || "").trim();
