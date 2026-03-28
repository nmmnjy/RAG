# 部署拓扑方案（V1 骨架）

## 1. 总体拓扑

```text
[User Browser]
      |
      v
[Vercel Edge/Frontend (Next.js)]
      |
      | HTTPS /api/v1/*
      v
[FastAPI Service (Container Runtime)]
      | \
      |  \ SQL + pgvector / Storage / Auth
      |   v
      | [Supabase (Postgres + pgvector + Storage + Realtime)]
      |
      +--> [LLM / Embedding Provider]

[Monitoring/Alert Channel]
  <- logs/metrics/traces from Frontend + Backend
```

## 2. 组件职责
- 前端（Vercel）：承载 Web UI、鉴权态透传、调用后端 API。
- 后端（FastAPI）：文档处理、检索、问答、评测 API 编排。
- Supabase：结构化数据、向量检索（pgvector）、对象存储、基础审计数据。
- 外部模型服务：Embedding 与 LLM 推理。
- 监控告警：采集可用性/错误率/时延并按级别通知。

## 3. 网络与安全边界
- 前端仅暴露公开站点域名。
- 后端只暴露必要 API，限制 CORS 白名单来源。
- Supabase 使用最小权限密钥：前端仅 `SUPABASE_ANON_KEY`，后端使用 `SUPABASE_SERVICE_ROLE_KEY`（仅服务端）。
- 所有服务统一注入 `APP_ENV`，禁止跨环境混用密钥。

## 4. 回滚入口
- 前端：Vercel 项目面板回滚到上一个 Deployment。
- 后端：容器平台回滚到上一个镜像 tag（`release-<timestamp>`）。
- 数据：Supabase 采用迁移版本回滚（仅允许向后兼容迁移进入 prod）。
