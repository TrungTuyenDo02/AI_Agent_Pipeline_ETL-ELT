// Khuôn dữ liệu trả về từ API FastAPI (khớp src/api/requests.py, src/models/*, src/services/catalog.py).

export type RunStatus =
  | "running"
  | "waiting_clarification"
  | "waiting_plan_review"
  | "waiting_schema"
  | "waiting_rescue"
  | "waiting_review"
  | "approved"
  | "failed";

export interface RunSummary {
  target?: string | null;
  mode?: string | null;
  fix_attempts?: number;
  rescue_count?: number;
  review_rounds?: number;
  optimization?: string | null;
  improvement_pct?: number | null;
  llm_calls?: number;
  tokens?: number;
  cost_usd?: number;
  simulated?: boolean;
  workspace?: string | null;
  error?: string;
}

export interface RunRecord {
  id: string;
  request_text: string;
  requester: string;
  status: RunStatus;
  provider: string;
  model: string;
  created_at: string;
  updated_at: string;
  summary: RunSummary;
}

export interface StepEvent {
  node: string;
  label: string;
  ok: boolean;
  detail: string;
  seconds: number;
  tokens: number;
  finished_at?: number; // epoch giây (máy chủ); chỉ có với bước chạy trong phiên máy chủ hiện tại
}

/** Node đang chạy (sự kiện "bắt đầu node" thật của LangGraph). */
export interface CurrentNode {
  node: string;
  label: string;
  stage: string | null;
  started_at: number;
  elapsed_s: number;
  /** Trung vị thời gian ĐO THẬT các lần trước; null khi chưa đủ mẫu (không ước lượng). */
  typical_s: number | null;
  samples: number;
  /** Mô tả việc đang làm, ghép từ state thật — KHÔNG phải log đo. */
  activity: string[];
}

export interface ClarifyQuestion {
  id: string;
  question: string;
  options: string[];
}

export interface PlanStep {
  title: string;
  detail: string;
  reason: string;
}

export interface PlanPending {
  kind: "plan";
  summary: string;
  steps: PlanStep[];
  spec: Spec;
  sources: string[];
  next_steps: string;
}

export type Pending =
  | { kind: "clarify"; unknowns: string[]; questions: ClarifyQuestion[] }
  | PlanPending
  | { kind: "schema"; report: SchemaReport }
  | { kind: "rescue"; error: string; fix_attempts: number }
  | { kind: "review"; run_id: string; requester: string };

export interface OutputColumn {
  name: string;
  type: string;
  description?: string;
  references?: string;
}

export interface Spec {
  target?: string;
  sources?: { name: string; kind: string }[];
  mode?: string;
  mode_reason?: string;
  grain?: string[];
  output_columns?: OutputColumn[];
  metrics?: { name: string; description: string }[];
  filters?: string[];
  assumptions?: string[];
  plan_summary?: string;
  plan?: PlanStep[];
}

export interface MeasuredItem {
  node: string;
  check: string;
  result: string;
  passed: boolean | null;
}

export interface Evidence {
  measured?: MeasuredItem[];
  claimed?: string[];
}

export interface QueryMetrics {
  median_ms: number;
  runs: number;
  peak_memory_mb?: number | null;
}

export interface Optimization {
  original_sql?: string;
  proposed_sql?: string;
  findings?: { rule: string; message: string }[];
  before?: QueryMetrics | null;
  after?: QueryMetrics | null;
  improvement_pct?: number | null;
  decision?: "applied" | "skipped";
  reason?: string;
  attempts?: number;
  equivalence?: { dataset: string; equal: boolean; detail: string }[];
  llm_cost_usd?: number;
  explanation?: string;
  warehouse_hints?: string[];
}

export interface Sandbox {
  passed?: boolean;
  error?: string;
  target_rows?: number;
  sample?: Record<string, string>[];
  models_ok?: number;
  models_total?: number;
  tests_ok?: number;
  tests_total?: number;
}

export interface AnsweredQuestion {
  id: string;
  question: string;
  answer: string;
}

export interface RunDetail {
  record: RunRecord;
  busy: boolean;
  pending: Pending | null;
  events: StepEvent[];
  spec: Spec;
  answered: AnsweredQuestion[];
  evidence: Evidence;
  optimization: Optimization;
  sandbox: Sandbox;
  code_notes: string[];
  test_notes: string[];
  stages?: Stage[];
  usage?: UsageReport;
  current?: CurrentNode | null;
  schema_report?: SchemaReport | Record<string, never>;
  schema_decision?: { by?: string; renames?: Record<string, string> };
  value_filters?: ValueFilter[];
  reconciliation?: RowReconciliation[];
}

/** Mục 8: một đề xuất sửa do code dựng (Reviewer quyết, agent không tự áp dụng). */
export interface SchemaProposal {
  kind: "added" | "type_changed" | "new_values" | "removed" | "rename";
  column: string;
  message: string;
  snippet: string;
  file: string;
}

export interface SourceChange {
  source: string;
  has_baseline: boolean;
  added: Record<string, string>;
  removed: Record<string, string>;
  type_changed: Record<string, [string, string]>;
  rename_candidates: [string, string][];
  new_values: Record<string, string[]>;
  proposals: SchemaProposal[];
}

/** Cấu trúc nguồn so với bản Reviewer đã duyệt (src/services/schema_watch.py). */
export interface SchemaReport {
  checked: boolean;
  note: string;
  changes: SourceChange[];
  blocking: boolean;
}

/** Mục 9: so sánh cột với giá trị cụ thể trong code sinh ra. */
export interface ValueFilter {
  file: string;
  line: number;
  column: string;
  values: string[];
  context: string;
  expression: string;
  in_spec: boolean;
}

/** Mục 9: số dòng raw → staging của một nguồn. */
export interface RowReconciliation {
  model: string;
  source: string;
  rows_in: number;
  rows_out: number;
}

/** Một dòng nhật ký kiểm toán (màn Admin). */
export interface AuditEntry {
  at: string;
  actor_name: string;
  action: string;
  target: string;
  outcome: string;
  ip: string;
  detail: Record<string, unknown>;
}

export type StageState = "waiting" | "running" | "passed" | "failed" | "human";

/** Một nút E/V/J trên đường ống (src/agents/stages.py). */
export interface Stage {
  id: string;
  code: string;
  label: string;
  kind: "E" | "V" | "J";
  state: StageState;
  detail: string;
}

export interface UsageRow {
  task: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  cost_usd: number;
  seconds: number;
}

/** Token/chi phí/thời gian LLM theo node (src/services/cost.usage_breakdown). */
export interface UsageReport {
  rows: UsageRow[];
  cache_hit_rate: number | null;
  simulated: boolean;
}

export interface RunFiles {
  code_files: Record<string, string>;
  test_files: Record<string, string>;
  previous_files: Record<string, string>;
}

export type Layer = "source" | "staging" | "mart";

export interface ColumnInfo {
  name: string;
  type: string;
  null_pct: number | null;
  is_key: boolean;
}

export interface TableInfo {
  id: string;
  name: string;
  layer: Layer;
  columns: ColumnInfo[];
  rows: number | null;
  duplicate_keys: number | null;
  file: string;
  group?: string;
  description?: string;
}

export interface JoinInfo {
  left: string;
  right: string;
  how: string;
  model: string;
  match_pct?: number | null;
}

export interface LineageEdge {
  source: string;
  target: string;
}

export interface CatalogView {
  tables: TableInfo[];
  lineage: LineageEdge[];
  joins: JoinInfo[];
}

/** Hồ sơ dữ liệu (đo bằng code, 0 token): chất lượng + phân bố từng cột, vấn đề, dòng xem trước đã che PII. */
export type ColumnKind = "number" | "date" | "text" | "bool" | "nested";

export interface ValueCount {
  label: string;
  count: number;
}

export interface ColumnProfile {
  name: string;
  type: string;
  kind: ColumnKind;
  is_key: boolean;
  filled: number;
  nulls: number;
  blank: number;
  invalid: number;
  case_variants: number;
  formats: string[];
  distinct: number;
  minimum: string | null;
  maximum: string | null;
  mean: number | null;
  zeros: number;
  top: ValueCount[];
  other: number;
  bins: ValueCount[];
  near_unique: boolean;
}

export interface ProfileIssue {
  level: "fail" | "warn" | "info";
  column: string;
  text: string;
}

export interface TableProfile {
  id: string;
  name: string;
  layer: Layer;
  rows: number;
  columns: ColumnProfile[];
  preview: (string | null)[][];
  issues: ProfileIssue[];
  duplicate_keys: number | null;
  keys: string[];
  rows_in: number | null;
  dataset: string;
  datasets: string[];
  file: string;
}

export interface AgentStatus {
  status: string;
  agent: string;
  llm_provider: string;
  models: string;
  simulated: boolean;
}

export interface ErrorEntry {
  id: number;
  code: string;
  signature: string;
  description: string;
  cause: string;
  fix: string;
  sql_before: string;
  sql_after: string;
  occurrences: number;
  approved: boolean;
  warnings: string[];
}

export interface Accepted {
  run_id: string;
  status: string;
  message: string;
}

/** Vai trò (kiểm ở backend; web chỉ dùng để ẩn/hiện nút): engineer tạo yêu cầu, reviewer duyệt, admin quản lý tài khoản. */
export type Role = "engineer" | "reviewer" | "admin";

/** Người dùng của phiên đăng nhập (GET /auth/me). */
export interface CurrentUser {
  id: number;
  name: string;
  display_name: string;
  role: Role;
}

/** Tài khoản trong màn quản trị (không có mật khẩu/chuỗi băm). */
export interface AdminUser {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
}
