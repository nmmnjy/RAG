import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";

export default function KbsPage(): React.JSX.Element {
  return (
    <SectionBlock title="知识库管理" description="可先开发：列表、创建弹窗、基础筛选。">
      <Card>
        <CardTitle>知识库列表（占位）</CardTitle>
        <CardDescription>后续联调接口后补充：分页、编辑、删除与权限控制。</CardDescription>
        <div className="mt-4">
          <Button>新建知识库</Button>
        </div>
      </Card>
    </SectionBlock>
  );
}
