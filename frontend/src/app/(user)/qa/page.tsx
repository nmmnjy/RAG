import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";
import { demoQaResult, demoQaState } from "@/features/qa/mock-data";
import { buildWorkflowNodes } from "@/features/workflow/state-machine";

const statusVariantMap = {
  todo: "default",
  in_progress: "warning",
  success: "success",
  warning: "warning",
  error: "danger"
} as const;

export default function QaPage(): React.JSX.Element {
  const nodes = buildWorkflowNodes(demoQaState);

  return (
    <div className="space-y-6">
      <SectionBlock title="用户问答" description="当前为页面骨架。后续联调后接入真实检索与答案生成接口。">
        <Card>
          <CardTitle>提问区</CardTitle>
          <CardDescription>支持选择知识库范围、输入问题、触发检索与生成。</CardDescription>
          <div className="mt-4 flex flex-col gap-3 md:flex-row">
            <input
              className="h-10 flex-1 rounded-lg border border-[var(--border)] bg-white px-3 text-sm outline-none focus:border-[var(--brand)]"
              placeholder="请输入问题（占位）"
            />
            <Button>开始问答</Button>
          </div>
        </Card>
      </SectionBlock>

      <SectionBlock title="状态流转" description="上传 -> 解析 -> 索引构建 -> 检索 -> 问答">
        <div className="grid gap-3 md:grid-cols-5">
          {nodes.map((node) => (
            <Card key={node.key} className="space-y-2 p-4">
              <CardTitle className="text-sm">{node.label}</CardTitle>
              <Badge variant={statusVariantMap[node.status]}>{node.status}</Badge>
            </Card>
          ))}
        </div>
      </SectionBlock>

      <SectionBlock title="答案与引用" description="字段遵循 PRD：answer/citations/confidence/refuse_reason">
        <Card>
          <CardTitle>答案</CardTitle>
          <CardDescription>{demoQaResult.answer}</CardDescription>
          <div className="mt-3 flex items-center gap-3">
            <Badge variant="success">confidence: {demoQaResult.confidence}</Badge>
            <Button variant="secondary">提交有用反馈</Button>
            <Button variant="ghost">提交无用反馈</Button>
          </div>
          <div className="mt-4 space-y-2">
            {demoQaResult.citations.map((item) => (
              <div key={item.chunk_id} className="rounded-lg bg-[var(--surface-muted)] p-3 text-sm">
                [{item.chunk_id}] {item.citation}
              </div>
            ))}
          </div>
        </Card>
      </SectionBlock>
    </div>
  );
}
