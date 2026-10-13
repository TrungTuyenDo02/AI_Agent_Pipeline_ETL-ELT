// Chữ của trang đăng nhập, hai ngôn ngữ (CLAUDE.md 9.2: giao diện chính là tiếng Việt; EN chỉ dành cho trang giới thiệu/đăng nhập).

export type Lang = "vi" | "en";
export const LANG_KEY = "p113.lang";

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
  heroTitle: string;
  heroSub: string;
  quote: string;
  tabsLabel: string;
  tabs: { about: string; run: string; data: string };
  about: { title: string; text: string }[];
  aboutNote: string;
  runSteps: string[];
  runOpen: string;
  accountsTitle: string;
  accountsHint: string;
  roles: { engineer: string; reviewer: string; admin: string };
  dataIntro: string;
  datasets: { name: string; detail: string }[];
  dataNote: string;
  copy: string;
  copied: string;
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
    heroTitle: "Từ một câu yêu cầu đến pipeline đã chạy thử.",
    heroSub:
      "P-113 lập kế hoạch, sinh model dbt và DAG Airflow, chạy thử trong sandbox DuckDB, tìm query chậm và đề xuất tối ưu. Người duyệt xem bằng chứng rồi mới merge.",
    quote: "“Agent chỉ thấy cấu trúc bảng, không bao giờ thấy dữ liệu thật.”",
    tabsLabel: "Thông tin dự án",
    tabs: { about: "Giới thiệu", run: "Chạy thử", data: "Dữ liệu mẫu" },
    about: [
      { title: "Lập kế hoạch", text: "Hỏi lại khi chưa rõ, trình kế hoạch để bạn duyệt." },
      { title: "Sinh code", text: "Model dbt, DAG Airflow và test do agent viết." },
      { title: "Chạy thử", text: "Chặn SQL nguy hiểm, chạy thật trong DuckDB." },
      { title: "Tối ưu và duyệt", text: "Chỉ áp dụng khi kết quả giống hệt và nhanh hơn." },
    ],
    aboutNote: "Nguyên tắc: người phán đoán, agent thực thi, code thuần kiểm chứng.",
    runSteps: [
      "Cài Python 3.11 và Node.js 20.9 trở lên, rồi cài thư viện (xem demo/README.md).",
      "Chạy lệnh bên dưới trong thư mục dự án.",
      "Mở http://localhost:3000 và đăng nhập bằng một tài khoản demo.",
    ],
    runOpen: "Lệnh chạy demo (LLM mô phỏng, không cần khóa API):",
    accountsTitle: "Tài khoản demo",
    accountsHint: "Bấm để điền sẵn. Mật khẩu cố định, chỉ dùng cho máy demo.",
    roles: { engineer: "Engineer", reviewer: "Reviewer", admin: "Admin" },
    dataIntro: "Dữ liệu công khai hoặc giả lập, không có dữ liệu công ty:",
    datasets: [
      {
        name: "P113 Retail (giả lập)",
        detail: "8 hệ thống, 19 bảng, bẩn có chủ đích: đơn trùng, ngày lẫn định dạng, tiền “1.075.000”.",
      },
      { name: "TPC-H (sf 0,1)", detail: "Bộ chuẩn để đo query chậm và hiệu quả tối ưu." },
      { name: "ELT-Bench-Verified (một phần)", detail: "10 task, 34 bảng để đo độ đúng của pipeline sinh ra." },
    ],
    dataNote: "Giao diện chỉ hiển thị cấu trúc bảng, không hiển thị dữ liệu thật.",
    copy: "Sao chép",
    copied: "Đã chép",
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
    heroTitle: "From one sentence to a pipeline that already ran.",
    heroSub:
      "P-113 plans the work, generates dbt models and Airflow DAGs, runs them in a DuckDB sandbox, finds slow queries and suggests optimisations. A reviewer checks the evidence before anything is merged.",
    quote: "“The agent only sees table structure, never the real data.”",
    tabsLabel: "Project information",
    tabs: { about: "About", run: "Try it", data: "Sample data" },
    about: [
      { title: "Plan", text: "Asks when unclear, then shows a plan for you to approve." },
      { title: "Generate", text: "dbt models, Airflow DAGs and tests written by the agent." },
      { title: "Run", text: "Blocks unsafe SQL, then runs it for real in DuckDB." },
      { title: "Optimise and review", text: "Applied only when results are identical and faster." },
    ],
    aboutNote: "Principle: humans judge, agents execute, plain code verifies.",
    runSteps: [
      "Install Python 3.11 and Node.js 20.9+, then the dependencies (see demo/README.md).",
      "Run the command below in the project folder.",
      "Open http://localhost:3000 and sign in with a demo account.",
    ],
    runOpen: "Demo command (simulated LLM, no API key needed):",
    accountsTitle: "Demo accounts",
    accountsHint: "Click to fill in. Fixed passwords, for demo machines only.",
    roles: { engineer: "Engineer", reviewer: "Reviewer", admin: "Admin" },
    dataIntro: "Public or synthetic data only, no company data:",
    datasets: [
      {
        name: "P113 Retail (synthetic)",
        detail: "8 systems, 19 tables, deliberately dirty: duplicate orders, mixed dates, “1.075.000” amounts.",
      },
      { name: "TPC-H (sf 0.1)", detail: "Standard benchmark for slow queries and optimiser gains." },
      { name: "ELT-Bench-Verified (subset)", detail: "10 tasks, 34 tables to measure pipeline correctness." },
    ],
    dataNote: "The UI shows table structure only, never real data.",
    copy: "Copy",
    copied: "Copied",
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
export const DEMO_COMMAND = "python demo/run_demo.py";
