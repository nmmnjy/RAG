# 前端模块骨架（06）

## 技术栈
- Next.js（App Router）
- Tailwind CSS v4
- shadcn/ui 风格基础组件（Button/Card/Badge）

## 启动
```bash
npm install
npm run dev
```

## 页面路由
- `/qa` 用户问答页
- `/history` 问答历史页
- `/citations/[citationId]` 引用详情页
- `/admin/kbs` 知识库管理
- `/admin/documents` 文档管理
- `/admin/tasks` 任务状态
- `/admin/logs` 日志看板

## 类型定义
- `src/types/domain.ts` PRD 关键字段
- `src/types/api.ts` API 响应与错误结构
- `src/types/workflow.ts` 状态流转

## 状态机
- `src/features/workflow/state-machine.ts` 将上传、解析、索引、检索、问答状态映射为 UI 节点状态。
