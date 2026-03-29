# 08 部署与运维骨架

本目录用于承接 `docs/tasks/08_部署与运维.md` 的工程化落地准备，目标是让后续线程可以直接接入部署配置与运维流程。

## 目录说明
- `topology/`：整体部署拓扑与流量路径。
- `environments/`：`dev/test/prod` 环境变量模板与注入规范。
- `vercel/`：前端 Vercel 部署骨架与脚本。
- `supabase/`：FastAPI 服务容器化与 Supabase 接入骨架。
- `monitoring/`：日志、指标、告警基线。
- `runbooks/`：发布、回滚、故障巡检手册。
- `scripts/`：预检、健康检查等通用脚本。

## 快速使用
1. 根据 `environments/.env.*.example` 生成各环境真实 `.env` 文件。
2. 执行 `scripts/preflight.ps1 -Environment <dev|test|prod> -Profile <core|vector|qa|all>` 校验变量完整性。
3. 前端按 `vercel/deploy-frontend.ps1` 与 `vercel/vercel.json` 部署。
4. 后端按 `supabase/deploy-backend.ps1`（容器）部署，并连接 Supabase。
5. 发布后执行 `scripts/health-check.ps1` 进行基础可用性验证。

## 本地演示与一键检查
- 前端构建：`scripts/local-frontend.ps1 -Action build`
- 后端关键测试：`scripts/local-backend.ps1 -Action test -TestScope key`
- 离线评测：`scripts/local-evaluation.ps1 -Dataset qa_demo_v1`
- 一键验收：`scripts/local-acceptance.ps1 -EvalDataset qa_demo_v1`
- 运行手册：`runbooks/local-demo-runbook.md`

## 对齐 00 模块基线
- 环境变量统一使用大写下划线命名。
- API 路径保持版本前缀（示例：`/api/v1/...`）。
- 错误结构统一为：`code`、`message`、`details`、`request_id`、`trace_id`。
- 日志基础字段：`timestamp`、`level`、`service`、`env`、`request_id`、`trace_id`、`span_id`、`user_id`、`kb_id`、`doc_id`。
