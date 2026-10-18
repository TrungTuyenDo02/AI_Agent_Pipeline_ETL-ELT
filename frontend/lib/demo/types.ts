// Khuôn của bộ dữ liệu mẫu (chế độ khách). fixtures.ts khai báo `satisfies DemoFixtures` nên API đổi khuôn
// (lib/types.ts) mà chưa sinh lại dữ liệu mẫu thì `npm run typecheck` báo lỗi ngay.
import type {
  AgentStatus,
  CatalogView,
  ErrorEntry,
  GlossaryTerm,
  RunDetail,
  RunFiles,
  SchemaReport,
  SourceView,
  TableProfile,
} from "../types";

export type DemoPhase = "intake" | "plan" | "build" | "approve";

/** Một khung "đang chạy": phần khác ảnh chụp cuối giai đoạn, kéo dài `dur` giây, đã xong `events_count` bước. */
export interface DemoFrame {
  dur: number;
  events_count: number;
  patch: Partial<RunDetail>;
}

export interface DemoFixtures {
  request: string;
  stoppedRequest: string;
  /** Ảnh chụp lúc dừng chờ người; `events` của ảnh sau luôn nối tiếp ảnh trước. */
  snapshots: { clarify: RunDetail; plan: RunDetail; review: RunDetail; approved: RunDetail };
  phases: Record<DemoPhase, DemoFrame[]>;
  files: RunFiles;
  catalog: CatalogView;
  profiles: Record<string, TableProfile>;
  /** Lần chạy đã dừng; `eventOffsets` = giây kể từ lúc bắt đầu lần chạy của từng bước. */
  stopped: { detail: RunDetail; eventOffsets: number[]; files: RunFiles };
  status: AgentStatus;
  sourcesCatalog: CatalogView;
  schemaReport: SchemaReport;
  errors: ErrorEntry[];
  glossary: GlossaryTerm[];
  sources: SourceView[];
}
