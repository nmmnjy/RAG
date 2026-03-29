import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";

interface CitationDetailPageProps {
  params: Promise<{ citationId: string }>;
  searchParams: Promise<{
    chunk_id?: string;
    doc_id?: string;
    section_path?: string;
    snippet?: string;
  }>;
}

export default async function CitationDetailPage({ params, searchParams }: CitationDetailPageProps): Promise<React.JSX.Element> {
  const { citationId } = await params;
  const query = await searchParams;

  return (
    <SectionBlock title="引用详情" description="支持引用原文定位、上下文展开和权限校验提示。">
      <Card>
        <CardTitle>citation_id: {citationId}</CardTitle>
        <CardDescription>用于溯源核验，展示本次问答携带的最小引用字段。</CardDescription>
        <div className="mt-4 space-y-2 text-sm">
          <p>chunk_id: {query.chunk_id ?? "-"}</p>
          <p>doc_id: {query.doc_id ?? "-"}</p>
          <p>section_path: {query.section_path ?? "-"}</p>
          <p>snippet: {query.snippet ?? "-"}</p>
        </div>
      </Card>
    </SectionBlock>
  );
}
