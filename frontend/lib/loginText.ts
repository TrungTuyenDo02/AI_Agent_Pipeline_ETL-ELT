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
  canvasLabel: string;
  pointsLabel: string;
  points: { icon: "sandbox" | "reviewer" | "optimize"; title: string; text: string }[];
  flowLabel: string;
  flow: { code: string; label: string; kind: FlowKind; hint: string }[];
  legendLabel: string;
  legend: { kind: FlowKind; label: string }[];
  toolsLabel: string;
  tools: string[];
  statsLabel: string;
  /** value: số lớn (phần trăm); detail: số gốc để đối chiếu; hint: điều kiện đo (hiện khi rê chuột). Lấy từ bảng Kết quả của README. */
  highlights: { value: string; label: string; detail: string; hint: string }[];
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
    docs: "Giới thiệu dự án",
    guestHint: "Không cần tài khoản. Kết quả là mẫu dựng sẵn, không do AI chạy thật.",
    contactText:
      "Tài khoản do quản trị viên của công ty cấp, không tự đăng ký. Gửi cho quản trị viên tên đăng nhập và vai trò cần dùng (Engineer hoặc Reviewer); họ sẽ cấp hoặc đặt lại mật khẩu cho bạn.",
    contactMail: "Gửi email cho quản trị viên",
    heroTitle: "Từ một câu yêu cầu đến pipeline đã chạy thử.",
    heroSub: "Sinh dbt và Airflow, chạy thử trong sandbox. Agent không bao giờ thấy dữ liệu thật.",
    canvasLabel: "Tổng quan dự án",
    pointsLabel: "Điểm nổi bật",
    points: [
      { icon: "sandbox", title: "An toàn", text: "Chỉ chạy trong sandbox DuckDB, không chạm production." },
      { icon: "reviewer", title: "Có người duyệt", text: "Reviewer xem diff và bằng chứng rồi mới merge." },
      { icon: "optimize", title: "Tự tối ưu", text: "Agent đo và viết lại query chậm, chỉ giữ khi kết quả giống hệt." },
    ],
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
        value: "93%",
        label: "lỗi cố ý bị bộ kiểm chứng bắt",
        detail: "14/15 ca · 0 token",
        hint: "Mutation test 2026-10-16: cố ý sửa sai pipeline, bộ kiểm chứng bằng code phải bắt được.",
      },
      {
        value: "86%",
        label: "thời gian truy vấn được cắt giảm",
        detail: "TPC-H · kết quả giống hệt",
        hint: "TPC-H sf=0,1, truy vấn viết tay = 100%: sau tối ưu (luật cố định + sqlglot) cả bộ còn 14% thời gian.",
      },
      {
        value: "100%",
        label: "ca nguồn đổi cấu trúc không lọt sai",
        detail: "6/6 ca · 0 sai âm thầm",
        hint: "Mô phỏng 6 kiểu backend đổi nguồn không báo trước: 4 chặn sớm, 1 vô hại, 1 cảnh báo; 0 báo nhầm.",
      },
      {
        value: "92%",
        label: "mã nguồn được test tự động phủ",
        detail: "1.225 test đạt",
        hint: "Chạy ở chế độ mock, 2026-10-18: độ phủ 92,05%, ngưỡng CI 60%.",
      },
    ],
    accountsTitle: "Tài khoản demo",
    accountsHint: "Bấm để điền sẵn. Mật khẩu cố định, chỉ dùng cho máy demo.",
    roles: { engineer: "Engineer", reviewer: "Reviewer", admin: "Admin" },
    footer: "© 2026 PipeSmith · Dự án P-113. Tài khoản do quản trị viên cấp.",
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
    docs: "About the project",
    guestHint: "No account needed. Results are prebuilt samples, not produced by a live AI run.",
    contactText:
      "Accounts are issued by your company administrator; there is no self-signup. Send them your username and the role you need (Engineer or Reviewer) and they will issue or reset your password.",
    contactMail: "Email the administrator",
    heroTitle: "From one sentence to a pipeline that already ran.",
    heroSub: "Generates dbt and Airflow, test-runs it in a sandbox. The agent never sees real data.",
    canvasLabel: "Project overview",
    pointsLabel: "Highlights",
    points: [
      { icon: "sandbox", title: "Safe", text: "Runs only in a DuckDB sandbox, never touches production." },
      { icon: "reviewer", title: "Human review", text: "A reviewer checks the diff and evidence before any merge." },
      {
        icon: "optimize",
        title: "Self-optimising",
        text: "The agent measures and rewrites slow queries, kept only if results match.",
      },
    ],
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
        value: "93%",
        label: "seeded bugs caught by the checks",
        detail: "14/15 cases · 0 tokens",
        hint: "Mutation test 2026-10-16: pipelines are broken on purpose and the plain-code checks must catch it.",
      },
      {
        value: "86%",
        label: "query time cut",
        detail: "TPC-H · identical results",
        hint: "TPC-H sf=0.1, hand-written queries = 100%: after optimisation (fixed rules + sqlglot) the suite takes 14% of the time.",
      },
      {
        value: "100%",
        label: "source changes caught, none slip through",
        detail: "6/6 cases · 0 silent errors",
        hint: "Six ways a backend can change a source unannounced: 4 blocked early, 1 harmless, 1 warned; 0 false alarms.",
      },
      {
        value: "92%",
        label: "of the code covered by automated tests",
        detail: "1,225 tests passing",
        hint: "Run in mock mode, 2026-10-18: 92.05% coverage, CI threshold 60%.",
      },
    ],
    accountsTitle: "Demo accounts",
    accountsHint: "Click to fill in. Fixed passwords, for demo machines only.",
    roles: { engineer: "Engineer", reviewer: "Reviewer", admin: "Admin" },
    footer: "© 2026 PipeSmith · Project P-113. Accounts issued by an administrator.",
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
