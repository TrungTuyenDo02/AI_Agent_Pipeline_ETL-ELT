// "Máy chủ" của chế độ khách: trả lời đúng các đường dẫn /api/v1/... mà web dùng, bằng dữ liệu mẫu trong trình duyệt.
// Luật vai trò, bước đang chờ và câu báo lỗi chép theo backend (src/api/*.py) để khách thấy đúng hành vi thật.
// Không có lệnh gọi mạng nào ở đây. Nạp bằng import() động từ lib/api.ts nên không làm nặng trang khi đăng nhập thường.

import { ApiError } from "../api";
import { GUEST_USERS, guestRole, type GuestRole } from "../guest";
import type { Accepted, RunRecord, TableProfile } from "../types";

import {
  advance,
  buildDetail,
  catalogOf,
  filesOf,
  isBusy,
  loadState,
  recordOf,
  saveState,
  startPhase,
  type DemoRun,
  type DemoState,
  type RunPhase,
} from "./engine";
import { FIXTURES } from "./fixtures";

const FORBIDDEN = "Bạn không có quyền thực hiện thao tác này.";
const BUSY = "Lần chạy đang chạy, vui lòng đợi.";
const NOT_FOUND_RUN = "Không tìm thấy lần chạy này.";
const NO_SAMPLE = "Chế độ khách chưa có dữ liệu mẫu cho mục này. Đăng nhập để dùng đầy đủ.";
/** Hồ sơ dữ liệu mẫu theo mã bảng ("raw.<nguồn>", "main.<model>"). */
const PROFILES: Record<string, TableProfile> = FIXTURES.profiles;
const READ_ONLY = "Chế độ khách không lưu thay đổi này. Đăng nhập để dùng đầy đủ.";
/** Điểm dừng chờ người ứng với `kind` của backend (runner.check_resumable). */
const WAITS: Record<string, RunPhase> = { clarify: "clarify", plan: "plan_review", review: "review" };

/** Đường dẫn chưa có dữ liệu mẫu (khác với kết quả null hợp lệ). */
const UNHANDLED = Symbol("unhandled");
type Reply = unknown;

const ok = (body: unknown): Reply => body;
const fail = (status: number, detail: string): never => {
  throw new ApiError(detail, status);
};

function role(): GuestRole {
  return guestRole() ?? "engineer";
}

function need(...roles: GuestRole[]): void {
  if (!roles.includes(role())) fail(403, FORBIDDEN);
}

function parseBody(body: BodyInit | null | undefined): Record<string, unknown> {
  if (typeof body !== "string" || !body) return {};
  try {
    const value = JSON.parse(body) as unknown;
    return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function accepted(runId: string, message: string): Reply {
  return { run_id: runId, status: "running", message } satisfies Accepted;
}

/** Lần chạy phải rảnh và đang chờ đúng bước (giống `_pending` ở backend). */
function pending(run: DemoRun, kind: string): void {
  if (isBusy(run)) fail(409, BUSY);
  if (run.phase !== WAITS[kind]) fail(409, `Lần chạy ${run.id} không ở bước chờ '${kind}'.`);
}

function listRecords(state: DemoState, now: number): RunRecord[] {
  return state.runs.map((run) => recordOf(run, now)).sort((a, b) => b.created_at.localeCompare(a.created_at));
}

function profileFor(table: string, dataset: string): TableProfile {
  const profile = PROFILES[table];
  if (!profile) fail(404, "Không tìm thấy bảng này.");
  if (dataset !== "sandbox") fail(404, "Chế độ khách chỉ có hồ sơ dữ liệu của bộ chạy thử (sandbox).");
  return { ...profile, datasets: ["sandbox"], dataset: "sandbox" };
}

function runRoutes(run: DemoRun, rest: string, method: string, body: Record<string, unknown>, now: number): Reply {
  const id = run.id;
  if (method === "GET") {
    if (rest === "") return ok(buildDetail(run, now));
    if (rest === "/files") return ok(filesOf(run));
    if (rest === "/catalog") return ok(catalogOf(run));
    return UNHANDLED;
  }
  if (method !== "POST") return UNHANDLED;
  switch (rest) {
    case "/answers": {
      need("engineer");
      pending(run, "clarify");
      const answers = (body.answers ?? {}) as Record<string, string | string[]>;
      const questions =
        FIXTURES.snapshots.clarify.pending?.kind === "clarify" ? FIXTURES.snapshots.clarify.pending.questions : [];
      const valid = questions.every((q) => {
        const value = answers[q.id];
        const picked = Array.isArray(value) ? value : [value];
        return picked.length > 0 && picked.every((v) => typeof v === "string" && q.options.includes(v));
      });
      if (!valid) fail(422, "Cần chọn đáp án có sẵn cho mỗi câu hỏi.");
      run.answers = answers;
      startPhase(run, "plan", now);
      return accepted(id, "Đã nhận, agent chạy tiếp.");
    }
    case "/plan": {
      need("engineer");
      pending(run, "plan");
      if (body.decision === "revise" && !text(body.note)) fail(422, "Yêu cầu sửa kế hoạch thì cần ghi chú cần sửa gì.");
      startPhase(run, body.decision === "revise" ? "plan" : "build", now);
      return accepted(id, "Đã nhận, agent chạy tiếp.");
    }
    case "/review": {
      need("reviewer");
      if (body.decision === "reject" && !text(body.note)) fail(422, "Từ chối thì cần ghi chú để agent biết sửa gì.");
      if (isBusy(run)) fail(409, BUSY);
      if (run.phase !== "review") fail(409, `Lần chạy ${id} không ở bước chờ duyệt.`);
      if (body.decision === "reject") {
        run.reviewRounds += 1;
        startPhase(run, "build", now);
        return accepted(id, "Đã từ chối, agent đang sửa theo ghi chú.");
      }
      startPhase(run, "approve", now);
      return accepted(id, "Đã duyệt.");
    }
    case "/retry":
      need("engineer");
      return fail(409, "Lần chạy mẫu này không chạy lại được trong chế độ khách. Đăng nhập để chạy thật.");
    case "/rescue":
    case "/input":
    case "/drift":
    case "/schema":
      need("engineer");
      return fail(409, `Lần chạy ${id} không ở bước chờ '${rest.slice(1)}'.`);
    case "/patch-plan":
    case "/patch":
      need("engineer");
      return fail(409, "Không có thay đổi cấu trúc nào đang mở ảnh hưởng tới lần chạy này.");
    default:
      return UNHANDLED;
  }
}

function route(state: DemoState, method: string, url: URL, body: Record<string, unknown>, now: number): Reply {
  const path = url.pathname.replace(/\/$/, "");
  const query = url.searchParams;
  const runMatch = /^\/runs\/([^/]+)(\/[a-z-]+)?$/.exec(path);
  if (runMatch && runMatch[1] !== "") {
    const run = state.runs.find((r) => r.id === runMatch[1]);
    if (!run) return fail(404, NOT_FOUND_RUN);
    if (runMatch[2] === "/profile" && method === "GET") {
      if (!catalogOf(run).tables.length) fail(404, "Không tìm thấy bảng này.");
      return ok(profileFor(query.get("table") ?? "", query.get("dataset") ?? "sandbox"));
    }
    return runRoutes(run, runMatch[2] ?? "", method, body, now);
  }
  const key = `${method} ${path}`;
  switch (key) {
    case "GET /auth/me":
      return ok(GUEST_USERS[role()]);
    case "POST /auth/logout":
      return ok({ ok: true });
    case "GET /status":
      return ok(FIXTURES.status);
    case "GET /runs":
      return ok(listRecords(state, now).slice(0, Number(query.get("limit") ?? 20) || 20));
    case "POST /runs": {
      need("engineer");
      const request = text(body.request_text);
      if (request.length < 5) fail(422, "Yêu cầu quá ngắn. Hãy mô tả bảng số liệu bạn cần (nguồn, chỉ số, điều kiện).");
      state.seq += 1;
      const run: DemoRun = {
        id: `mau-moi-${state.seq}`,
        kind: "main",
        request: request.slice(0, 4000),
        requester: GUEST_USERS.engineer.name,
        createdAt: now,
        phase: "intake",
        phaseAt: now,
        starts: { intake: now },
        reviewRounds: 0,
        updatedAt: now,
      };
      state.runs.push(run);
      return accepted(run.id, "Đã nhận yêu cầu, agent đang chạy.");
    }
    case "GET /reviews/queue":
      return ok(listRecords(state, now).filter((r) => r.status === "waiting_review"));
    case "GET /catalog/sources":
      return ok(FIXTURES.sourcesCatalog);
    case "GET /catalog/sources/profile": {
      const profile = PROFILES[`raw.${query.get("table") ?? ""}`];
      return profile ? ok(profile) : fail(404, "Không tìm thấy bảng này.");
    }
    case "GET /catalog/schema-changes":
      return ok(FIXTURES.schemaReport);
    case "GET /errors":
      return ok(
        FIXTURES.errors
          .filter((e) => state.errorDecisions[e.id] !== "reject")
          .map((e) => (state.errorDecisions[e.id] === "approve" ? { ...e, approved: true } : e)),
      );
    case "GET /memory":
      return ok([]);
    case "GET /glossary":
      return ok(FIXTURES.glossary);
    case "GET /sources":
      return ok(FIXTURES.sources);
    case "GET /departments":
      return ok([{ id: 1, name: "Mặc định" }]);
    case "GET /schema-changes":
      return ok([]);
  }
  const errorAction = /^POST \/errors\/(\d+)\/(approve|reject)$/.exec(key);
  if (errorAction) {
    need("reviewer");
    state.errorDecisions[errorAction[1]] = errorAction[2] as "approve" | "reject";
    return ok({ ok: true });
  }
  if (path.startsWith("/admin")) return fail(403, FORBIDDEN);
  if (method !== "GET") return fail(403, READ_ONLY);
  return UNHANDLED;
}

/** Thay cho `fetch` khi là khách: trả nguyên văn JSON như máy chủ (hoặc ném ApiError với `detail` tiếng Việt). */
export async function demoRequest(method: string, path: string, body?: BodyInit | null): Promise<string> {
  const now = Date.now();
  const state = loadState(now);
  let changed = false;
  for (const run of state.runs) changed = advance(run, now) || changed;
  const before = JSON.stringify(state);
  try {
    const reply = route(state, method.toUpperCase(), new URL(path, "http://demo.local"), parseBody(body), now);
    if (reply === UNHANDLED) fail(404, NO_SAMPLE);
    return JSON.stringify(reply);
  } finally {
    if (changed || JSON.stringify(state) !== before) saveState(state);
  }
}
