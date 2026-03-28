import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";

const logRows = [
  { type: "qa", request_id: "req_001", trace_id: "trace_001", level: "info" },
  { type: "retrieval", request_id: "req_002", trace_id: "trace_001", level: "info" },
  { type: "task", request_id: "req_003", trace_id: "trace_002", level: "error" }
];

export default function LogsPage(): React.JSX.Element {
  return (
    <SectionBlock title="日志看板" description="依赖统一日志规范。当前可先开发字段展示和筛选交互框架。">
      <Card>
        <CardTitle>日志列表（占位）</CardTitle>
        <CardDescription>字段示例：request_id / trace_id / level / type。</CardDescription>
        <ul className="mt-4 space-y-2 text-sm">
          {logRows.map((item) => (
            <li key={item.request_id} className="rounded-lg bg-[var(--surface-muted)] px-3 py-2">
              {item.type} | {item.level} | request_id={item.request_id} | trace_id={item.trace_id}
            </li>
          ))}
        </ul>
      </Card>
    </SectionBlock>
  );
}
