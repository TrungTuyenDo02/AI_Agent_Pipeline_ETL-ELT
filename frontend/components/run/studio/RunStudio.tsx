"use client";

import { StageGuide } from "../../guide/Guide";
import { ResultCard } from "../ResultCard";
import { useRun } from "../RunContext";
import { RunLog } from "../RunLog";
import { UsageSummary } from "../UsageSummary";
import { FlowPanel, MetricsPanel } from "./Panels";
import { ClarifyStep, PlanStep, RequestStep, TrackerStep } from "./Steps";
import { useRunAttention } from "./useRunAttention";

/**
 * Màn tổng quan lần chạy: mỗi lúc chỉ mở bước đang cần chú ý. Yêu cầu, làm rõ, kế hoạch đã xong thì gộp vào một dòng thu gọn;
 * "Nhật ký chạy" luôn hiện ngay dưới tiến trình; token, chi phí, sơ đồ luồng và kết quả mẫu nằm trong ngăn
 * "Chi tiết kỹ thuật" (mặc định đóng).
 */
export function RunStudio() {
  const { detail } = useRun();
  useRunAttention(detail);
  if (!detail) return null;
  const waitingOnPlanning = detail.pending?.kind === "clarify" || detail.pending?.kind === "plan";
  const trackerStarted = (detail.stages ?? []).some(
    (s) => !["planner", "clarify", "spec_check", "plan_review"].includes(s.id) && s.state !== "waiting",
  );
  const settled = !waitingOnPlanning && Boolean(detail.spec.plan?.length) && trackerStarted;
  const steps = (
    <>
      <RequestStep detail={detail} />
      <ClarifyStep detail={detail} />
      <PlanStep detail={detail} />
    </>
  );
  return (
    <div className="studio-flow">
      <StageGuide />
      {settled ? (
        <details className="card done-group">
          <summary>
            <span className="badge ok">Đã xong</span>
            <strong>Yêu cầu, làm rõ và kế hoạch</strong>
            <span className="muted truncate">{detail.record.request_text}</span>
          </summary>
          <div className="done-group-body">{steps}</div>
        </details>
      ) : (
        steps
      )}
      <TrackerStep detail={detail} />
      <RunLog detail={detail} />
      <UsageSummary />
      <details className="card tech-details">
        <summary>
          <strong>Chi tiết kỹ thuật</strong>
          <span className="muted">Luồng dữ liệu, kết quả mẫu, chỉ số kiểm thử</span>
        </summary>
        <div className="studio tech-body">
          <div className="studio-main">
            {(detail.sandbox?.passed || (detail.code_notes ?? []).length > 0) && <ResultCard />}
          </div>
          <aside className="studio-side">
            <MetricsPanel detail={detail} />
            <FlowPanel detail={detail} />
          </aside>
        </div>
      </details>
    </div>
  );
}
