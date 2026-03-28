import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";
import { demoDocuments } from "@/features/admin/mock-data";

export default function DocumentsPage(): React.JSX.Element {
  return (
    <SectionBlock title="文档管理" description="可先开发：上传面板、文档表格、状态标签。">
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
