// Nguồn dữ liệu cho panel "Nhật ký chạy" (CLAUDE.md yêu cầu 2). Mọi dòng dựng từ dữ liệu THẬT API đã trả:
//  - chế độ gọn: trạng thái từng bước (`stages`, luôn có) → mỗi bước một câu tiếng Việt dễ hiểu;
//  - chi tiết kỹ thuật: nhật ký bước gốc (`events`) + việc đang làm (`current`).
// Backend CHƯA có luồng log riêng: `events` chỉ còn trong phiên máy chủ đang chạy.
// TODO(thay bằng API): khi backend có endpoint log (ví dụ GET /runs/{id}/logs) chỉ cần sửa `buildRunLog`; panel giữ nguyên.

import { plainStepLabel } from "./format";
import type { RunDetail, Stage } from "./types";

export type LogLevel = "info" | "ok" | "warn" | "error";

export interface LogLine {
  id: string;
  /** Giờ máy chủ (epoch giây); null khi không còn nhật ký gốc. */
  time: number | null;
  level: LogLevel;
  step: string;
  /** Mã kỹ thuật của bước (E1, V2…): chỉ hiện trong tooltip / chế độ kỹ thuật. */
  code: string;
  text: string;
  /** Câu giải thích + bước tiếp theo (chỉ dòng lỗi/cảnh báo). */
  hint?: string;
}

export const LEVEL_LABELS: Record<LogLevel, string> = { info: "INFO", ok: "OK", warn: "CẢNH BÁO", error: "LỖI" };

// Node của graph thuộc từng bước (khớp src/agents/stages.py) — để lấy giờ thật cho dòng gọn.
const STAGE_NODES: Record<string, string[]> = {
  prepare: ["ingest", "profiler", "mock_data"],
  schema: ["schema_guard"],
  sandbox: ["sandbox_run"],
  review: ["review", "package", "finalize"],
};

const withDetail = (text: string, detail: string) => (detail ? `${text}: ${detail}` : text);

/** Câu dễ hiểu khi bước đã xong. */
const DONE: Record<string, (d: string) => string> = {
  planner: () => "Đã hiểu yêu cầu và lập kế hoạch",
  clarify: (d) => withDetail("Đã trả lời câu hỏi làm rõ", d),
  spec_check: () => "Kế hoạch đủ thông tin để bắt đầu",
  plan_review: () => "Kế hoạch đã được đồng ý",
  prepare: (d) => withDetail("Đã nạp và xem nhanh dữ liệu nguồn", d),
  schema: () => "Cấu trúc bảng nguồn khớp bản đã duyệt",
  codegen: (d) => withDetail("Đã viết code pipeline", d),
  testgen: (d) => withDetail("Đã viết bài kiểm tra kết quả", d),
  safety: () => "Code qua kiểm tra an toàn",
  sandbox: () => "Chạy thử thành công trên dữ liệu mẫu",
  rescue: (d) => withDetail("Đã xử lý tình huống cần cứu hộ", d),
  optimizer: () => "Đã thử tìm cách chạy nhanh hơn",
  compare: (d) =>
    d === "skipped"
      ? "Bỏ qua so sánh trước/sau (không có bản tối ưu)"
      : withDetail("Đã so kết quả trước/sau tối ưu", d),
  review: (d) => (d ? `Code ${d}` : "Code đã được duyệt"),
};

/** Câu giải thích đơn giản + gợi ý bước tiếp theo khi bước lỗi. */
const FAIL_HINT: Record<string, string> = {
  planner: "Agent chưa hiểu yêu cầu. Thử viết lại yêu cầu rõ hơn: cần bảng gì, tính theo ngày/tháng nào.",
  spec_check: "Kế hoạch còn thiếu thông tin. Trả lời câu hỏi làm rõ hoặc bổ sung yêu cầu rồi chạy lại.",
  prepare: "Không đọc được dữ liệu nguồn. Kiểm tra trang Dữ liệu nguồn xem bảng có tồn tại và đọc được không.",
  schema: "Bảng nguồn đổi cấu trúc so với bản đã duyệt. Xem đề xuất sửa ở tab Duyệt code rồi xác nhận.",
  codegen: "Agent chưa viết được code. Chạy lại; nếu vẫn lỗi, viết yêu cầu cụ thể hơn.",
  testgen: "Agent chưa viết được bài kiểm tra. Chạy lại lần chạy này.",
  safety: "Code có lệnh không an toàn hoặc sai tên bảng/cột. Agent tự sửa; nếu vẫn lỗi, xem chi tiết kỹ thuật.",
  sandbox:
    "Code chạy thử bị lỗi trên dữ liệu mẫu. Agent tự sửa vài lần; hết lượt thì bật chi tiết kỹ thuật để xem lỗi gốc hoặc gửi lại yêu cầu rõ hơn.",
  optimizer: "Không tìm được bản chạy nhanh hơn. Pipeline vẫn dùng được với code gốc.",
  compare: "Bản tối ưu cho kết quả khác bản gốc nên bị loại. Pipeline giữ code gốc, không cần làm gì thêm.",
};
const GENERIC_HINT = "Bước này chưa hoàn thành. Bật “Xem chi tiết kỹ thuật” để xem thông báo gốc, rồi thử chạy lại.";

const WAITING_ON_YOU: Record<string, string> = {
  clarify: "Đang chờ bạn trả lời câu hỏi làm rõ",
  plan: "Đang chờ bạn duyệt kế hoạch",
  schema: "Đang chờ bạn xác nhận thay đổi cấu trúc nguồn",
  rescue: "Agent cần bạn quyết định cách xử lý lỗi",
  review: "Đang chờ Reviewer duyệt code",
};

function lastEventTime(detail: RunDetail, stage: Stage): number | null {
  const nodes = STAGE_NODES[stage.id] ?? [stage.id];
  const event = [...(detail.events ?? [])].reverse().find((e) => nodes.includes(e.node));
  return event?.finished_at ?? null;
}

function stageLine(detail: RunDetail, stage: Stage): LogLine | null {
  const base = { id: stage.id, time: lastEventTime(detail, stage), step: stage.label, code: stage.code };
  switch (stage.state) {
    case "passed":
      return { ...base, level: "ok", text: (DONE[stage.id] ?? ((d) => withDetail(stage.label, d)))(stage.detail) };
    case "failed":
      return {
        ...base,
        level: "error",
        text: withDetail(`${stage.label} không đạt`, stage.detail),
        hint: FAIL_HINT[stage.id] ?? GENERIC_HINT,
      };
    case "running": {
      const activity = detail.current?.activity?.[0];
      return { ...base, level: "info", text: `Đang ${stage.label.toLowerCase()}${activity ? ` — ${activity}` : "…"}` };
    }
    case "human": {
      const text = WAITING_ON_YOU[detail.pending?.kind ?? ""] ?? `Đang chờ người ở bước ${stage.label.toLowerCase()}`;
      return {
        ...base,
        level: "warn",
        text,
        hint: "Mở bước đang sáng ở trên để trả lời; agent sẽ chạy tiếp ngay sau đó.",
      };
    }
    default:
      return null;
  }
}

/** Chế độ gọn: mỗi bước đã chạy một dòng tiếng Việt dễ hiểu. */
export function buildCompactLog(detail: RunDetail): LogLine[] {
  const lines = (detail.stages ?? []).map((s) => stageLine(detail, s)).filter((l): l is LogLine => l !== null);
  if (detail.record.status === "failed" && !lines.some((l) => l.level === "error")) {
    lines.push({
      id: "run-failed",
      time: null,
      level: "error",
      step: "Lần chạy",
      code: "",
      text: "Lần chạy đã dừng trước khi xong",
      hint: GENERIC_HINT,
    });
  }
  if (detail.record.status === "paused")
    lines.push({
      id: "run-paused",
      time: null,
      level: "warn",
      step: "Lần chạy",
      code: "",
      text: "Đã tạm dừng theo yêu cầu, trước bước kế tiếp",
      hint: "Bấm Tiếp tục để chạy tiếp. Các bước đã xong không chạy lại.",
    });
  else if (detail.record.pause_requested)
    lines.push({
      id: "run-pausing",
      time: null,
      level: "info",
      step: "Lần chạy",
      code: "",
      text: "Đang chờ tạm dừng: bước hiện tại chạy xong thì dừng",
      hint: "",
    });
  return lines;
}

/** Chi tiết kỹ thuật: nhật ký bước gốc từ máy chủ (OK/LỖI do code đo) + dòng việc đang làm. */
export function buildTechnicalLog(detail: RunDetail): LogLine[] {
  const lines: LogLine[] = (detail.events ?? []).map((e, i) => ({
    id: `${e.node}-${i}`,
    time: e.finished_at ?? null,
    level: e.ok ? "ok" : "error",
    step: plainStepLabel(e.label),
    code: e.node,
    text:
      `${e.node} · ${e.detail || "(không có thông báo)"} · ${e.seconds.toFixed(1)}s` +
      (e.tokens > 0 ? ` · ${e.tokens} token` : ""),
    hint: e.ok ? undefined : (FAIL_HINT[e.node] ?? GENERIC_HINT),
  }));
  if (lines.length === 0) {
    // Máy chủ đã khởi động lại: không còn log gốc → hiện trạng thái lưu ở checkpoint (vẫn là dữ liệu thật)
    for (const s of detail.stages ?? []) {
      if (s.state === "waiting") continue;
      lines.push({
        id: `stage-${s.id}`,
        time: null,
        level: s.state === "failed" ? "error" : s.state === "human" ? "warn" : s.state === "running" ? "info" : "ok",
        step: s.label,
        code: s.code,
        text: `[checkpoint] ${s.code} ${s.id} state=${s.state}${s.detail ? ` detail="${s.detail}"` : ""}`,
      });
    }
  }
  const current = detail.busy ? detail.current : null;
  if (current) {
    lines.push({
      id: `live-${current.node}`,
      time: current.started_at,
      level: "info",
      step: plainStepLabel(current.label),
      code: current.node,
      text: `${current.node} đang chạy · ${current.activity.join(" · ") || "…"} (mô tả, không phải log đo)`,
    });
  }
  return lines;
}

/** Có log gốc từ máy chủ không (để nói rõ với người dùng khi chỉ còn trạng thái checkpoint). */
export const hasRawEvents = (detail: RunDetail) => (detail.events ?? []).length > 0;

export function logClock(epochSeconds: number | null): string {
  if (!epochSeconds) return "--:--:--";
  return new Date(epochSeconds * 1000).toLocaleTimeString("vi-VN", { hour12: false });
}

export function logAsText(lines: LogLine[]): string {
  return lines
    .map(
      (l) =>
        `[${logClock(l.time)}] ${LEVEL_LABELS[l.level].padEnd(8)} ${l.step}: ${l.text}${l.hint ? `\n    → ${l.hint}` : ""}`,
    )
    .join("\n");
}
