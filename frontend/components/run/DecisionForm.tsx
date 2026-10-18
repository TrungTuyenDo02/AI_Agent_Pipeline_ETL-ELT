"use client";

import { useState } from "react";

import { STATUS_LABELS } from "@/lib/format";

import { useApp, useHasRole } from "../AppContext";
import { ConfirmDialog } from "../ConfirmDialog";
import { RoleNote } from "../Topbar";
import { Card, ErrorBox } from "../ui";
import { useRun } from "./RunContext";

export function DecisionForm() {
  const { detail, act } = useRun();
  const reviewer = useHasRole("reviewer");
  const { guest } = useApp();
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  if (!detail) return null;
  const blocked = Boolean(detail.drift?.recheck?.blocked); // cấu trúc nguồn đã đổi sau lúc sinh code
  const waiting = detail.record.status === "waiting_review" && !detail.busy && reviewer;

  async function decide(decision: "approve" | "reject") {
    setSending(true);
    setError(
      await act(
        "/review",
        { decision, note },
        decision === "approve"
          ? "Đã duyệt. Engineer sẽ thấy trong thông báo."
          : "Đã gửi yêu cầu sửa, agent đang sửa theo ghi chú.",
      ),
    );
    setSending(false);
  }

  return (
    <Card title="Quyết định (J2)">
      <div className="stack" style={{ gap: 10 }}>
        {!waiting && (
          <div className={detail.record.status === "approved" ? "alert ok" : "alert info"}>
            <span>
              {detail.busy
                ? "Agent đang chạy, chờ một chút."
                : detail.record.status === "approved"
                  ? guest
                    ? "Đã duyệt (giả lập trong chế độ khách). Đăng nhập để duyệt và tải gói code thật."
                    : "Đã duyệt. Tải gói code (.zip) ở góc trên để mở Pull Request."
                  : `Trạng thái: ${STATUS_LABELS[detail.record.status]}.`}
            </span>
          </div>
        )}
        {blocked && (
          <div className="alert danger" role="alert">
            <span>
              Cấu trúc nguồn đã đổi sau khi agent sinh code, nên chưa duyệt được bản này:
              <ul className="plain">
                {detail.drift?.recheck?.breaking.map((c) => (
                  <li key={`${c.table}-${c.detail}`}>{c.detail}</li>
                ))}
              </ul>
              Hãy từ chối kèm ghi chú, hoặc nhờ Engineer bấm &quot;Đề xuất bản vá&quot; ở trang Thay đổi cấu trúc để
              chạy lại sandbox trên cấu trúc mới.
            </span>
          </div>
        )}
        {detail.record.status === "waiting_review" && <RoleNote need="reviewer" />}
        <label htmlFor="review-note">Ghi chú (bắt buộc khi từ chối — agent sẽ sửa theo ghi chú)</label>
        <textarea
          id="review-note"
          rows={4}
          maxLength={2000}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Ví dụ: loại đơn hoàn khỏi doanh thu; đổi tên cột revenue thành revenue_vnd"
          disabled={!waiting}
        />
        {error && <ErrorBox message={error} />}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button
            type="button"
            className="btn danger"
            disabled={!waiting || sending || !note.trim()}
            onClick={() => decide("reject")}
          >
            Từ chối và ghi chú
          </button>
          <button
            type="button"
            className="btn ok"
            disabled={!waiting || sending || blocked}
            onClick={() => setConfirming(true)}
          >
            Duyệt
          </button>
          <ConfirmDialog
            open={confirming}
            onOpenChange={setConfirming}
            title="Duyệt pipeline này?"
            confirmLabel="Duyệt"
            onConfirm={() => decide("approve")}
          >
            <p>
              Bảng đích: <strong className="mono">{detail.record.summary.target ?? "chưa rõ"}</strong>.
            </p>
            <p>
              Quyết định được ghi vào nhật ký kiểm toán (ai, lúc nào) và báo cho Engineer. Agent không tự merge:
              Engineer tải gói code và mở Pull Request.
            </p>
          </ConfirmDialog>
        </div>
        <small className="muted">
          Duyệt xong: tải gói code (.zip) ở góc trên, đưa vào repo và mở Pull Request để CI/CD chạy. Agent không tự
          push.
        </small>
      </div>
    </Card>
  );
}
