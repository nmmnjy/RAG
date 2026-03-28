import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";

const taskRows = [
  { task_id: "task_001", stage: "parse", status: "in_progress", request_id: "req_001" },
  { task_id: "task_002", stage: "index", status: "success", request_id: "req_002" },
  { task_id: "task_003", stage: "index", status: "failed", request_id: "req_003" }
];

export default function TasksPage(): React.JSX.Element {
  return (
    <SectionBlock title="任务状态" description="依赖后端任务 API。当前可先完成表格框架、筛选器和状态样式。">
      <Card>
        <CardTitle>任务监控（占位）</CardTitle>
        <CardDescription>后续将接入轮询/订阅，显示解析、索引和失败重试入口。</CardDescription>
        <div className="mt-4 space-y-2">
          {taskRows.map((task) => (
            <div key={task.task_id} className="flex items-center justify-between rounded-lg bg-[var(--surface-muted)] px-3 py-2 text-sm">
              <span>
                {task.task_id} / {task.stage} / {task.request_id}
              </span>
              <Badge variant={task.status === "failed" ? "danger" : task.status === "success" ? "success" : "warning"}>{task.status}</Badge>
            </div>
          ))}
        </div>
      </Card>
    </SectionBlock>
  );
}
