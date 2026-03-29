import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";

const qaLogRows = [
  {
    ts: "2026-03-29T09:30:00+08:00",
    request_id: "req_001",
    kb_id: "kb_hr",
    query_text: "年假申请提前几天？",
    confidence: 0.84,
    refuse_reason: null
  },
  {
    ts: "2026-03-29T09:35:00+08:00",
    request_id: "req_002",
    kb_id: "kb_hr",
    query_text: "请给我不存在政策的答案",
    confidence: 0,
    refuse_reason: "QA_CONTEXT_EMPTY"
  }
];

export default function LogsPage(): React.JSX.Element {
  return (
    <SectionBlock title="日志看板" description="最小闭环：查看最近问答记录关键字段。">
      <Card>
        <CardTitle>最近问答记录</CardTitle>
        <CardDescription>字段：ts / request_id / kb_id / query_text / confidence / refuse_reason。</CardDescription>
        <div className="mt-4 space-y-2 text-sm">
          {qaLogRows.map((item) => (
            <div key={item.request_id} className="rounded-lg bg-[var(--surface-muted)] px-3 py-2">
              <p>
                {item.ts} | {item.request_id} | {item.kb_id}
              </p>
              <p className="mt-1 text-[#4f5645]">{item.query_text}</p>
              <p className="mt-1 text-xs text-[#5a6151]">
                confidence={item.confidence} | refuse_reason={item.refuse_reason ?? "null"}
              </p>
            </div>
          ))}
        </div>
      </Card>
    </SectionBlock>
  );
}
