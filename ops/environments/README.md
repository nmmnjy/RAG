# 环境划分与配置注入方案

## 1. 环境定义
- `dev`：个人/联调环境，可使用测试数据与宽松限流。
- `test`：集成测试与验收演练环境，配置尽量贴近 `prod`。
- `prod`：生产环境，严格密钥隔离、审计与告警。

## 2. 注入原则
- 非敏感变量：可通过平台环境变量或 `.env` 文件注入。
- 敏感变量：仅通过平台 Secret 管理器注入，禁止入库。
- 前端构建期变量统一以 `NEXT_PUBLIC_` 前缀暴露。
- 后端运行期变量不允许 `NEXT_PUBLIC_` 前缀。

## 3. 变量命名规范（对齐 00 基线）
- 统一 `UPPER_SNAKE_CASE`。
- 最小必填集合：`APP_ENV`、`APP_PORT`、`DB_URL`、`SUPABASE_URL`、`SUPABASE_KEY`、`LLM_API_KEY`、`EMBEDDING_MODEL`、`LOG_LEVEL`。
- API 错误对象字段保留：`code`、`message`、`details`、`request_id`、`trace_id`。

## 4. 文件说明
- `.env.shared.example`：跨环境通用键。
- `.env.dev.example`：开发环境覆盖项。
- `.env.test.example`：测试环境覆盖项。
- `.env.prod.example`：生产环境覆盖项（仅占位，不含真实值）。
