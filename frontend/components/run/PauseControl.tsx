"use client";

import { useState } from "react";

import { useApp } from "../AppContext";
import { Icon } from "../icons";
import { ErrorBox } from "../ui";
import { useRun } from "./RunContext";

const NOTE = "Hệ thống hoàn tất bước đang chạy rồi tạm dừng. Bước này vẫn có thể phát sinh chi phí AI.";

/**
 * Tạm dừng / tiếp tục một lần chạy thật (ADR 0016). Chỉ người tạo yêu cầu (Engineer) thấy; chế độ khách không có (demo không
 * mô phỏng tạm dừng). Đang chờ người trả lời/duyệt, đã xong hoặc lỗi: không hiện (trạng thái chờ tương ứng đã đủ rõ).
 */
export function PauseControl() {
  const { detail, act } = useRun();
  const { user, guest } = useApp();
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState("");
  if (!detail || guest || !user || user.role !== "engineer" || user.name !== detail.record.requester) return null;
  const { status, pause_requested: pausing } = detail.record;
  if (status !== "running" && status !== "paused") return null;

  async function send(path: string, done: string) {
    setSending(true);
    setFailure(await act(path, {}, done));
    setSending(false);
  }

  if (status === "paused")
    return (
      <div className="pause-control" role="status">
        <div className="pause-text">
          <strong>
            <Icon name="pause" size={16} weight="fill" /> Đã tạm dừng
          </strong>
          <span>
            {detail.record.summary.notice ||
              "Các bước đã xong được giữ nguyên. Tiếp tục sẽ chạy từ bước kế tiếp, không làm lại phần đã xong."}
          </span>
          {failure && <ErrorBox message={failure} />}
        </div>
        <button
          type="button"
          className="btn primary"
          disabled={sending}
          onClick={() => send("/resume", "Đã nhận, agent chạy tiếp.")}
        >
          <Icon name="sandbox" size={16} weight="fill" />
          {sending ? "Đang gửi…" : "Tiếp tục"}
        </button>
      </div>
    );

  return (
    <div className="pause-control" role="status">
      <div className="pause-text">
        {pausing && <strong>Đang chờ tạm dừng…</strong>}
        <span>{NOTE}</span>
        {failure && <ErrorBox message={failure} />}
      </div>
      <button
        type="button"
        className="btn"
        disabled={sending || pausing}
        aria-disabled={pausing || undefined}
        onClick={() => send("/pause", "Đã nhận yêu cầu tạm dừng.")}
      >
        <Icon name="pause" size={16} weight="fill" />
        {pausing ? "Đang chờ tạm dừng…" : sending ? "Đang gửi…" : "Tạm dừng"}
      </button>
    </div>
  );
}
