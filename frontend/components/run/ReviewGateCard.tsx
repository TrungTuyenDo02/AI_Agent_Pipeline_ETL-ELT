"use client";

import { formatTime } from "@/lib/format";
import type { DbtTestResult, GateCheck, GateStatus, RunDetail } from "@/lib/types";

import { Card, Empty, PassMark } from "../ui";
import { useRun } from "./RunContext";

const STATUS: Record<GateStatus, [string, string]> = {
  passed: ["Đạt", "badge ok"],
  failed: ["Không đạt", "badge danger"],
  unverified: ["Chưa kiểm chứng", "badge warn"],
};

/** Lý do không duyệt được; rỗng = được duyệt. API cũ không có `review_gate` → chưa kiểm chứng, không tự coi là đạt. */
export function gateProblems(detail: RunDetail): string[] {
  const gate = detail.review_gate;
  if (!gate) return ["Chưa có kết quả kiểm tra bắt buộc (chưa kiểm chứng)."];
  if (gate.passed) return [];
  return gate.checks.filter((c) => c.status !== "passed").map((c) => `${c.name}: ${c.reason}`);
}

function CheckRow({ check }: { check: GateCheck }) {
  const [label, tone] = STATUS[check.status];
  return (
    <li>
      <span className={tone}>{label}</span>{" "}
      <span>
        <strong>{check.name}</strong>
        {check.reason && <span className="muted">: {check.reason}</span>}
      </span>
    </li>
  );
}

/** Màn Reviewer: tổng hợp kiểm tra bắt buộc (chặn duyệt), kiểm tra bổ sung, quyết định tối ưu và lịch sử duyệt. */
export function ReviewGateCard() {
  const { detail } = useRun();
  if (!detail) return null;
  const gate = detail.review_gate;
  const opt = detail.optimization;
  const reviews = detail.reviews ?? [];
  return (
    <Card title="Kiểm tra trước khi duyệt">
      {!gate ? (
        <Empty>Chưa kiểm chứng: lần chạy này chưa có kết quả kiểm tra bắt buộc.</Empty>
      ) : (
        <>
          <p className="small">
            <span className={gate.passed ? "badge ok" : "badge danger"}>
              {gate.passed ? "Đủ điều kiện duyệt" : "Chưa được duyệt"}
            </span>{" "}
            Cả 4 kiểm tra bắt buộc phải đạt; thiếu bằng chứng được tính là chưa kiểm chứng.
          </p>
          <ul className="plain stack">
            {gate.checks.map((c) => (
              <CheckRow key={c.id} check={c} />
            ))}
          </ul>
          {gate.extra.length > 0 && (
            <>
              <h3>Bổ sung (không chặn duyệt)</h3>
              <ul className="plain stack">
                {gate.extra.map((c) => (
                  <CheckRow key={c.id} check={c} />
                ))}
              </ul>
            </>
          )}
        </>
      )}
      <h3>Quyết định tối ưu</h3>
      <p className="small">
        {opt.decision ? (
          <>
            <strong>{opt.decision === "applied" ? "Áp dụng bản mới" : "Giữ nguyên bản gốc"}:</strong>{" "}
            {opt.reason || "—"}
          </>
        ) : (
          "Chưa tới bước tối ưu."
        )}
      </p>
      <h3>Lịch sử duyệt</h3>
      {reviews.length === 0 ? (
        <p className="small muted">Chưa có quyết định nào.</p>
      ) : (
        <ul className="plain small">
          {reviews.map((r) => (
            <li key={`${r.decided_at}-${r.reviewer}`}>
              {formatTime(r.decided_at)} · <strong>{r.reviewer}</strong> ·{" "}
              {r.decision === "approve" ? "Duyệt" : "Từ chối"}
              {r.note ? `: ${r.note}` : ""}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export const TEST_KINDS: Record<DbtTestResult["kind"], [string, string]> = {
  optimizer: ["Bảo vệ bản tối ưu", "badge warn"],
  testgen: ["Testgen (độc lập với code)", "badge ok"],
  declared: ["Khai báo (yml)", "badge muted"],
};

/** Từng dbt test đã chạy ở lần sandbox cuối (V2): người duyệt thấy test nào bảo vệ cái gì, không chỉ con số x/y. */
export function DbtTestsCard() {
  const { detail } = useRun();
  if (!detail) return null;
  const tests = detail.dbt_tests ?? [];
  const passed = tests.filter((t) => ["pass", "success", "warn"].includes(t.status)).length;
  return (
    <Card title={`dbt test đã chạy trên sandbox (${passed}/${tests.length} đạt)`}>
      {tests.length === 0 ? (
        <Empty>Chưa đo: lần chạy này chưa có danh sách test (chưa chạy sandbox hoặc dữ liệu cũ).</Empty>
      ) : (
        <ul className="measured-list">
          {tests.map((t) => (
            <li key={t.name} className={["pass", "success", "warn"].includes(t.status) ? undefined : "fail"}>
              <PassMark passed={["pass", "success", "warn"].includes(t.status)} />
              <div>
                <div>
                  <strong className="mono">{t.name}</strong>{" "}
                  <span className={TEST_KINDS[t.kind][1]}>{TEST_KINDS[t.kind][0]}</span>
                </div>
                {t.message && <div className="node">{t.message}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
