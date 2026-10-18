import type { RunDetail } from "./types";

export type PipPose = "idle" | "notes" | "coding" | "review" | "error" | "done";

export interface PipState {
  pose: PipPose;
  title: string;
  message: string;
}

/** Display follows server state; the companion never invents progress or approves work. */
export function pipState(detail: RunDetail): PipState {
  const status = detail.record.status;
  if (status === "paused") {
    return {
      pose: "idle",
      title: "Pip nghỉ một nhịp",
      message: "Checkpoint vẫn được giữ. Bạn có thể tiếp tục khi sẵn sàng.",
    };
  }
  if (status === "approved") {
    return {
      pose: "done",
      title: "Pip đã hoàn tất!",
      message: "Lần chạy đã được duyệt. Bạn có thể xem và tải bộ code.",
    };
  }
  if (status === "failed" || status === "waiting_rescue") {
    return {
      pose: "error",
      title: "Pip cần bạn xem lại",
      message: "Có vấn đề cần xử lý. Xem thông báo và bằng chứng của lần chạy bên dưới.",
    };
  }
  if (status === "rejected_input") {
    return {
      pose: "notes",
      title: "Pip cần yêu cầu rõ hơn",
      message: "Xem gợi ý của hệ thống rồi mô tả lại bảng dữ liệu bạn cần.",
    };
  }
  if (detail.busy || status === "running") {
    if ((detail.queue_position ?? 0) > 0) {
      return { pose: "idle", title: "Pip đang chờ đến lượt", message: "Lần chạy đang nằm trong hàng đợi." };
    }
    if (detail.record.pause_requested) {
      return {
        pose: "coding",
        title: "Pip đang hoàn tất bước hiện tại",
        message: "Đã nhận yêu cầu tạm dừng. Pip sẽ nghỉ sau khi bước này kết thúc.",
      };
    }
    const node = detail.current?.node;
    const planning = node === "planner" || node === "input_gate" || node === "drift_gate" || node === "patch_start";
    return {
      pose: planning ? "notes" : "coding",
      title: planning ? "Pip đang chuẩn bị công việc" : "Pip đang làm việc",
      message: detail.current?.label || "Đang xử lý lần chạy. Tiến trình thật hiển thị ở bên dưới.",
    };
  }
  if (status === "waiting_input" || status === "waiting_clarification") {
    return {
      pose: "notes",
      title: "Pip đang lắng nghe bạn",
      message: "Trả lời câu hỏi để PipeSmith hiểu đúng yêu cầu trước khi đi tiếp.",
    };
  }
  return {
    pose: "review",
    title: "Pip chờ bạn xem và duyệt",
    message:
      status === "waiting_review"
        ? "Code đã tới bước chờ duyệt. Hãy xem bằng chứng và kết quả trước khi quyết định."
        : "Có một điểm cần bạn xác nhận. Xem nội dung bên dưới để tiếp tục.",
  };
}
