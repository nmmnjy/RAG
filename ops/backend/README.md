# 后端 FastAPI + Supabase 部署方案骨架

## 1. 目标
- FastAPI 以容器方式部署在托管容器平台（平台待主线程最终定版，如 Railway/Render/Fly.io）。
- Supabase 负责 Postgres + pgvector + Storage + Auth。

## 2. 必备环境变量
- `APP_ENV`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `DB_URL`
- `LLM_API_KEY`
- `CORS_ALLOW_ORIGINS`
- `API_VERSION`

## 3. 部署流程（骨架）
1. 构建后端镜像：`docker build -f ops/backend/Dockerfile.fastapi .`
2. 镜像推送到仓库（待主线程指定 registry）。
3. 在容器平台更新服务镜像并注入环境变量。
4. 发布后执行 `ops/scripts/health-check.ps1` 验证。

## 4. 回滚流程
1. 容器平台选择上一个稳定镜像 tag（`release-<timestamp>`）。
2. 重新部署并执行健康检查。
3. 如涉及 DB 迁移，按 `runbooks/rollback.md` 的迁移回退策略执行。
