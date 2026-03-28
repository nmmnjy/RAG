# 前端 Vercel 部署方案骨架

## 1. 项目绑定
1. 在 Vercel 创建项目并绑定前端目录（待主线程确定实际目录，例如 `frontend/`）。
2. 连接 Git 仓库，开启 Preview 与 Production。

## 2. 环境变量映射
- `Development`：使用 `ops/environments/.env.dev.example` 同名键。
- `Preview`：使用 `ops/environments/.env.test.example` 同名键。
- `Production`：使用 `ops/environments/.env.prod.example` 同名键。

必须注入的前端变量：
- `NEXT_PUBLIC_APP_ENV`
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## 3. 部署步骤
1. 配置 Build Command（示例）：`npm run build`
2. 配置 Output：Next.js 默认。
3. 首次部署后记录项目域名，回填到后端 `CORS_ALLOW_ORIGINS`。

## 4. 回滚步骤
1. Vercel 控制台进入 Deployments。
2. 选择上一个绿色状态版本。
3. 执行 Promote to Production。

## 5. 验证点
- 主页可访问，`/api/health`（如存在）返回 200。
- 前端请求后端时携带并透传 `x-request-id`/`x-trace-id`（实现接入时补齐）。
