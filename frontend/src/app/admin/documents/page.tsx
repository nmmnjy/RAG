import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";
import { demoDocuments } from "@/features/admin/mock-data";

export default function DocumentsPage(): React.JSX.Element {
  return (
    <SectionBlock title="文档管理" description="可先开发：上传面板、文档表格、状态标签。">
      <Card>
        <CardTitle>文档上传</CardTitle>
        <CardDescription>最小闭环入口：可见上传区域与任务状态跳转。当前为联调占位，不触发真实上传。</CardDescription>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <input className="h-10 rounded-lg border border-[var(--border)] bg-white px-3 text-sm" placeholder="kb_id" defaultValue="kb_hr" />
          <input className="h-10 rounded-lg border border-[var(--border)] bg-white px-3 text-sm md:col-span-2" type="file" />
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Button variant="secondary">上传文档（占位）</Button>
          <Link href="/admin/tasks" className="text-sm text-[var(--brand)] hover:underline">
            查看任务状态
          </Link>
        </div>
      </Card>
      <Card className="overflow-x-auto">
        <CardTitle>文档列表（占位）</CardTitle>
        <CardDescription>状态字段遵循 PRD：doc_id/kb_id/source/format/version/status。</CardDescription>
        <table className="mt-4 min-w-full text-left text-sm">
          <thead className="text-[#5a6151]">
            <tr>
              <th className="py-2 pr-4">doc_id</th>
              <th className="py-2 pr-4">kb_id</th>
              <th className="py-2 pr-4">source</th>
              <th className="py-2 pr-4">format</th>
              <th className="py-2 pr-4">version</th>
              <th className="py-2">status</th>
            </tr>
          </thead>
          <tbody>
            {demoDocuments.map((doc) => (
              <tr key={doc.doc_id} className="border-t border-[var(--border)]">
                <td className="py-3 pr-4">{doc.doc_id}</td>
                <td className="py-3 pr-4">{doc.kb_id}</td>
                <td className="py-3 pr-4">{doc.source}</td>
                <td className="py-3 pr-4">{doc.format}</td>
                <td className="py-3 pr-4">{doc.version}</td>
                <td className="py-3">
                  <Badge>{doc.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </SectionBlock>
  );
}
