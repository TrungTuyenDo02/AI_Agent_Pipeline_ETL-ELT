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
  pointsLabel: string;
  points: { icon: "sandbox" | "reviewer" | "optimize"; title: string; text: string }[];
  /** Demo động: luồng là minh họa (gắn nhãn); code là trích đoạn model thật của lần chạy mẫu, con số ở thẻ tốc độ là
   *  số đo thật (README, mục Kết quả). */
  demo: {
    label: string;
    tag: string;
    requestLabel: string;
    request: string;
    file: string;
    code: string[];
    run: string;
    /** Bảng kết quả cuối: 3 dòng đầu thật của fct_daily_revenue, chép từ lib/demo/fixtures.ts (scripts/demo_fixtures.py
     *  chạy luồng thật, dbt trong sandbox DuckDB, dữ liệu nguồn giả lập seed=42). Sinh lại fixtures thì chép lại. */
    table: { label: string; name: string; note: string; columns: string[]; rows: string[][]; more: string };
    resultValue: string;
    resultLabel: string;
    resultHint: string;
  };
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
    heroSub: "Lập kế hoạch, sinh dbt và Airflow, chạy thử trong sandbox. Người duyệt xem bằng chứng rồi mới merge.",
    quote: "“Agent chỉ thấy cấu trúc và thống kê, không bao giờ thấy dòng dữ liệu thật.”",
    canvasLabel: "Tổng quan dự án",
    pointsLabel: "Điểm nổi bật",
    points: [
      { icon: "sandbox", title: "An toàn", text: "Chỉ chạy trong sandbox DuckDB, không chạm production." },
      { icon: "reviewer", title: "Có người duyệt", text: "Reviewer xem diff và bằng chứng rồi mới merge." },
      { icon: "optimize", title: "Tự tối ưu", text: "Agent đo và viết lại query chậm, chỉ giữ khi kết quả giống hệt." },
    ],
    demo: {
      label: "Demo luồng chạy",
      tag: "Ví dụ minh họa",
      requestLabel: "Yêu cầu",
      request: "Gộp đơn hàng từ ba nguồn, tính doanh thu theo ngày.",
      file: "models/marts/fct_daily_revenue.sql",
      code: [
        "select order_date, count(*) as order_count,",
        "       cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd",
        "from deduped where status in ('completed') group by order_date",
      ],
      run: "Chạy thử trong sandbox: đạt",
      table: {
        label: "Kết quả demo",
        name: "fct_daily_revenue",
        note: "Bảng do pipeline AI sinh tạo ra khi chạy thật trong sandbox, trên dữ liệu mẫu",
        columns: ["Ngày", "Số đơn", "Doanh thu (₫)"],
        rows: [
          ["2026-09-01", "2", "5.168.000"],
          ["2026-09-02", "6", "8.608.000"],
          ["2026-09-03", "10", "16.402.000"],
        ],
        more: "3/30 dòng · dữ liệu mẫu",
      },
      resultValue: "7×",
      resultLabel: "Query nhanh hơn 7 lần",
      resultHint: "Số đo thật: bộ truy vấn TPC-H sau tối ưu chỉ còn 14% thời gian, kết quả giống hệt.",
    },
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
        detail: "1.214 test đạt",
        hint: "Chạy ở chế độ mock, 2026-10-18: độ phủ 91,99%, ngưỡng CI 60%.",
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
    docs: "About the project",
    guestHint: "No account needed. Results are prebuilt samples, not produced by a live AI run.",
    contactText:
      "Accounts are issued by your company administrator; there is no self-signup. Send them your username and the role you need (Engineer or Reviewer) and they will issue or reset your password.",
    contactMail: "Email the administrator",
    heroTitle: "From one sentence to a pipeline that already ran.",
    heroSub:
      "Plans the work, generates dbt and Airflow, runs it in a sandbox. A reviewer checks the evidence before any merge.",
    quote: "“The agent sees structure and statistics, never real data rows.”",
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
    demo: {
      label: "Run demo",
      tag: "Illustrative example",
      requestLabel: "Request",
      request: "Merge orders from three sources, revenue per day.",
      file: "models/marts/fct_daily_revenue.sql",
      code: [
        "select order_date, count(*) as order_count,",
        "       cast(coalesce(sum(amount_vnd), 0) as bigint) as revenue_vnd",
        "from deduped where status in ('completed') group by order_date",
      ],
      run: "Sandbox test run: passed",
      table: {
        label: "Demo result",
        name: "fct_daily_revenue",
        note: "Table produced by the AI-generated pipeline in a real sandbox run, on sample data",
        columns: ["Date", "Orders", "Revenue (₫)"],
        rows: [
          ["2026-09-01", "2", "5,168,000"],
          ["2026-09-02", "6", "8,608,000"],
          ["2026-09-03", "10", "16,402,000"],
        ],
        more: "3/30 rows · sample data",
      },
      resultValue: "7×",
      resultLabel: "Faster queries",
      resultHint: "Measured: the TPC-H query suite takes 14% of the time after optimisation, identical results.",
    },
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
        detail: "1,214 tests passing",
        hint: "Run in mock mode, 2026-10-18: 91.99% coverage, CI threshold 60%.",
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
