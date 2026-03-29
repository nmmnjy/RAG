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

## 4. 与 03/05 对齐的本地演示最小配置
- 03（向量化）必填建议：
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIM`
- `VECTOR_REPOSITORY`
- `VECTOR_REPOSITORY_ENABLE_REAL`
- `VECTOR_REPOSITORY_FALLBACK_TO_IN_MEMORY`
- 05（答案生成）必填建议：
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_PROVIDER_ENABLE_REAL`
- `LLM_PROVIDER_FALLBACK_TO_MOCK`
- 本地演示建议直接基于：`.env.local-demo.example`
- real-mode 联调建议基于：`.env.real-mode.example`

## 5. 文件说明
- `.env.shared.example`：跨环境通用键。
- `.env.dev.example`：开发环境覆盖项。
- `.env.test.example`：测试环境覆盖项。
- `.env.prod.example`：生产环境覆盖项（仅占位，不含真实值）。
- `.env.local-demo.example`：本地演示（前端+后端+评测）最小可运行模板。
- `.env.real-mode.example`：真实 provider 联调验收模板（需填真实密钥）。
