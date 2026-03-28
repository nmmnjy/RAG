import Link from "next/link";

import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";
import { demoHistory } from "@/features/qa/mock-data";

export default function HistoryPage(): React.JSX.Element {
  return (
    <SectionBlock title="问答历史" description="后续将接入分页、筛选和详情回放。">
      <Card className="overflow-x-auto">
        <CardTitle>历史记录</CardTitle>
        <CardDescription>用户可以查看问答结果、置信度和引用详情。</CardDescription>
        <table className="mt-4 min-w-full text-left text-sm">
          <thead className="text-[#5a6151]">
            <tr>
              <th className="py-2 pr-4">时间</th>
              <th className="py-2 pr-4">问题</th>
              <th className="py-2 pr-4">置信度</th>
              <th className="py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {demoHistory.map((item) => (
              <tr key={item.qa_id} className="border-t border-[var(--border)]">
                <td className="py-3 pr-4">{item.created_at}</td>
                <td className="py-3 pr-4">{item.question}</td>
                <td className="py-3 pr-4">{item.confidence}</td>
                <td className="py-3">
                  <Link href="/citations/chunk_001" className="text-[var(--brand)] hover:underline">
                    查看引用
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </SectionBlock>
  );
}
