import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";

interface CitationDetailPageProps {
  params: Promise<{ citationId: string }>;
}

export default async function CitationDetailPage({ params }: CitationDetailPageProps): Promise<React.JSX.Element> {
  const { citationId } = await params;

  return (
    <SectionBlock title="引用详情" description="支持引用原文定位、上下文展开和权限校验提示。">
      <Card>
        <CardTitle>citation_id: {citationId}</CardTitle>
        <CardDescription>此页面为占位。后续联调后将展示对应 chunk 的原文、文档来源与 section_path。</CardDescription>
      </Card>
    </SectionBlock>
  );
}
