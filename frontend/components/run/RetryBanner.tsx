"use client";

import { useState } from "react";

import { useHasRole } from "../AppContext";
import { Icon } from "../icons";
import { RoleNote } from "../Topbar";
import { ErrorBox } from "../ui";
import { useRun } from "./RunContext";

/**
 * Lần chạy lỗi nhưng còn checkpoint (LLM quá hạn, hết hạn mức, server khởi động lại giữa chừng): cho chạy lại từ bước lỗi.
 * Các bước đã xong giữ nguyên, không gọi lại LLM cho phần đã làm; chỉ làm lại bước đang dở.
 */
export function RetryBanner() {
  const { detail, act } = useRun();
  const engineer = useHasRole("engineer");
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState("");
  if (!detail?.retryable) return null;

  async function retry() {
    setSending(true);
    setFailure(await act("/retry", {}, "Đã nhận, agent chạy lại từ bước lỗi."));
    setSending(false);
  }

  return (
    <div className="alert danger retry-banner" role="alert">
      <div className="stack" style={{ gap: 6 }}>
        <span className="alert-text">
          <Icon name="failure" size={18} weight="fill" />
          <strong>Lần chạy dừng vì lỗi</strong>
        </span>
        <span>{detail.record.summary.error || "Có lỗi khi chạy một bước."}</span>
        <small>Các bước đã xong được giữ nguyên. Chạy lại chỉ làm lại bước đang dở, không lặp lại phần đã làm.</small>
        {!engineer && <RoleNote need="engineer" />}
        {failure && <ErrorBox message={failure} />}
      </div>
      <button type="button" className="btn primary" onClick={retry} disabled={sending || !engineer}>
        <Icon name="reload" size={16} />
        {sending ? "Đang gửi…" : "Chạy lại từ bước lỗi"}
      </button>
    </div>
  );
}
