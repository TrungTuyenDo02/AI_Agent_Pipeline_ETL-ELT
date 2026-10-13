import { Suspense } from "react";

import { AgentEfficiency } from "@/components/AgentEfficiency";
import { RunsTable } from "@/components/RunsTable";
import { Loading } from "@/components/ui";

export default function RunsPage() {
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Lần chạy</h1>
          <p>Mọi yêu cầu đã gửi: trạng thái, bảng đích, tối ưu, chi phí LLM. Lần chạy cần bạn xử lý được đánh dấu.</p>
        </div>
      </div>
      <AgentEfficiency />
      {/* bộ lọc đọc từ đường dẫn (?loc=…) nên cần Suspense khi dựng trang tĩnh */}
      <Suspense fallback={<Loading text="Đang tải danh sách lần chạy…" />}>
        <RunsTable />
      </Suspense>
    </>
  );
}
