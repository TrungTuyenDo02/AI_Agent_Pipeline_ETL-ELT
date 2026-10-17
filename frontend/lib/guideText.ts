// Chữ của phần hướng dẫn nhúng sẵn trong chế độ khách (components/guide/Guide.tsx). Chỉ hiện khi là khách.
// Viết cho người không rành kỹ thuật: mỗi câu ngắn, lời thường. Sửa nội dung ở đây, không cần đụng component.

import type { RunStatus } from "./types";

export const GUIDE_BANNER = {
  title: "Bạn đang ở Chế độ khách",
  text: "Mỗi bước có giải thích bằng lời thường. Mọi kết quả là dữ liệu mẫu.",
  login: "Đăng nhập để chạy thật",
  exit: "Thoát chế độ khách",
};

export type GuideStepId = "request" | "code" | "test" | "review";

/** Khối "Quy trình 4 bước"; `phase` khớp 4 giai đoạn của thanh tiến trình (PipelineTrack). */
export const GUIDE_STEPS: { id: GuideStepId; phase: string; title: string; text: string }[] = [
  {
    id: "request",
    phase: "understand",
    title: "Nhập yêu cầu",
    text: "Bạn tả bảng số liệu cần có. Agent hỏi lại chỗ chưa rõ và đưa kế hoạch để bạn đồng ý.",
  },
  {
    id: "code",
    phase: "build",
    title: "Xem code AI viết",
    text: "Agent viết code lấy và tính dữ liệu, kèm các bài kiểm tra tự động.",
  },
  {
    id: "test",
    phase: "verify",
    title: "Chạy thử an toàn",
    text: "Code chạy trên một bản sao dữ liệu tách riêng, không chạm hệ thống thật. Máy tự đo kết quả.",
  },
  {
    id: "review",
    phase: "review",
    title: "Người duyệt",
    text: "Một người khác xem lại thay đổi. Chỉ khi họ duyệt, pipeline mới được dùng thật.",
  },
];

export const GUIDE_STEP_STATE = {
  done: "Đã xong",
  running: "Đang làm",
  human: "Chờ người",
  failed: "Đã dừng ở đây",
  waiting: "Chưa tới",
} as const;

/** Khung giải thích ở từng giai đoạn của trang chi tiết lần chạy. */
export const GUIDE_NOTES = {
  request: {
    title: "Giai đoạn 1: hiểu yêu cầu",
    text: "Agent đọc câu bạn viết, hỏi lại điểm chưa rõ rồi đưa kế hoạch. Chưa có code nào được viết cho tới khi bạn đồng ý kế hoạch.",
  },
  code: {
    title: "Code AI viết gồm gì",
    text: "Hai phần: model dbt là các câu lệnh biến dữ liệu thô thành bảng số liệu; DAG Airflow là lịch để pipeline tự chạy mỗi ngày hoặc mỗi giờ.",
  },
  test: {
    title: "Chạy thử trong sandbox",
    text: "Sandbox là bản sao dữ liệu tách riêng, chạy hỏng cũng không ảnh hưởng gì. Dấu xanh nghĩa là kết quả đúng như kiểm tra mong đợi, dấu đỏ nghĩa là có chỗ lệch cần sửa.",
  },
  optimize: {
    title: "Tối ưu truy vấn chậm",
    text: "Agent tìm câu truy vấn chạy chậm và đề xuất cách viết nhanh hơn. Máy so trước và sau: chỉ dùng bản mới khi kết quả giống hệt và thời gian giảm đủ nhiều.",
  },
  review: {
    title: "Duyệt thay đổi",
    text: "Diff cho thấy dòng thêm và dòng bỏ so với bản trước. Chỉ khi Reviewer duyệt, pipeline mới được đưa vào dùng thật. Ở chế độ khách, nút Duyệt là giả lập.",
  },
};

/** Dòng giải thích theo trạng thái thật của lần chạy. */
export const STATUS_EXPLAIN: Record<RunStatus, string> = {
  running: "Agent đang làm việc. Trang tự cập nhật, bạn không cần tải lại.",
  waiting_input: "Yêu cầu chưa đủ thông tin. Hãy bổ sung theo gợi ý bên dưới.",
  waiting_drift: "Dữ liệu nguồn vừa đổi cấu trúc. Cần người xác nhận trước khi chạy tiếp.",
  waiting_clarification: "Agent cần bạn trả lời vài câu hỏi để hiểu đúng yêu cầu.",
  waiting_plan_review: "Agent đã lập kế hoạch. Đọc kế hoạch rồi bấm đồng ý để agent viết code.",
  waiting_schema: "Dữ liệu nguồn có cột bị đổi hoặc bị xóa. Cần người xác nhận trước khi chạy tiếp.",
  waiting_rescue: "Agent tự sửa lỗi chưa được. Cần người gợi ý cách sửa hoặc dừng lần chạy.",
  waiting_review: "Code đã chạy thử đạt. Đang chờ Reviewer xem thay đổi và quyết định.",
  approved: "Reviewer đã duyệt. Pipeline sẵn sàng để đưa vào dùng thật.",
  failed: "Lần chạy đã dừng và không chạy tiếp. Xem nhật ký chạy để biết dừng ở bước nào.",
  rejected_input: "Yêu cầu bị từ chối ở bước kiểm tra đầu vào nên chưa tốn công chạy.",
};

/** Câu giải thích dưới ô thống kê ở trang chủ (theo nhãn ô). */
export const STAT_EXPLAIN: Record<string, string> = {
  "Đã tạo": "Mọi yêu cầu bạn đã gửi.",
  "Chờ tôi": "Đang đợi bạn trả lời hoặc đồng ý.",
  "Chờ Reviewer": "Đã chạy thử, đợi người duyệt.",
  "Đã duyệt": "Đã duyệt, sẵn sàng dùng thật.",
  "Chờ duyệt": "Đang đợi bạn xem và quyết định.",
  "Sổ lỗi chờ": "Bài học từ lỗi cũ, chờ duyệt để dùng lại.",
  "Đang chờ Engineer": "Đang đợi người tạo yêu cầu trả lời.",
};

export const GUIDE_TRY = {
  title: "Bước 1: nói điều bạn cần",
  text: "Viết một câu nêu rõ: dữ liệu lấy từ đâu, muốn tính gì, theo ngày hay theo tháng.",
  button: "Thử ngay với ví dụ",
  example: "gộp đơn hàng 3 nguồn, tính doanh thu ngày",
};

export const GUIDE_GLOSSARY: { term: string; text: string }[] = [
  { term: "Pipeline", text: "Chuỗi bước tự động lấy dữ liệu, tính toán rồi đưa ra bảng số liệu dùng được." },
  { term: "Sandbox", text: "Bản sao dữ liệu tách riêng để chạy thử, chạy hỏng cũng không ảnh hưởng hệ thống thật." },
  { term: "Reviewer", text: "Người xem lại và quyết định có cho pipeline được dùng thật hay không." },
  {
    term: "dbt và DAG",
    text: "dbt là cách viết các bước tính toán bằng SQL; DAG là lịch cho biết bước nào chạy trước, chạy lúc nào.",
  },
  { term: "Diff", text: "Bảng so sánh cho thấy dòng nào được thêm, dòng nào bị bỏ so với bản trước." },
  { term: "Merge", text: "Đưa thay đổi đã duyệt vào bản chính thức để mọi người cùng dùng." },
];

export const GUIDE_DONE = {
  title: "Bạn vừa đi hết quy trình",
  text: "Từ một câu yêu cầu tới pipeline đã chạy thử và được duyệt. Đăng nhập để chạy với dữ liệu và AI thật.",
  login: "Đăng nhập để chạy thật",
  docs: "Xem tài liệu dự án",
};
