import { CreateRunForm } from "@/components/CreateRunForm";
import { RunsTable } from "@/components/RunsTable";
import { Card } from "@/components/ui";

export default function HomePage() {
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Lần chạy</h1>
          <p>Mô tả pipeline cần làm → agent lập kế hoạch, sinh dbt + DAG, chạy thử sandbox, tối ưu → bạn duyệt.</p>
        </div>
      </div>
      <Card title="Yêu cầu mới">
        <CreateRunForm />
      </Card>
      <RunsTable />
    </>
  );
}
