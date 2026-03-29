# 本地可演示运行手册（前端 + 后端 + 评测）

## 1. 环境准备
1. Node.js 20+（用于前端构建）
2. Python 3.11+（用于后端与评测）
3. 在项目根目录准备环境变量：
- 参考 `infra/environments/.env.local-demo.example`
- 至少保证 00 最小集合：`APP_ENV/APP_PORT/DB_URL/SUPABASE_URL/SUPABASE_KEY/LLM_API_KEY/EMBEDDING_MODEL/LOG_LEVEL`
- 对齐 03/05 本地演示配置：
  - 03：`EMBEDDING_PROVIDER/EMBEDDING_DIM/VECTOR_REPOSITORY/...`
  - 05：`LLM_PROVIDER/LLM_MODEL/LLM_PROVIDER_ENABLE_REAL/LLM_PROVIDER_FALLBACK_TO_MOCK`
4. 执行预检：
```powershell
.\infra\scripts\preflight.ps1 -Environment dev -Profile all
```

## 2. 启动顺序（演示联调）
1. 启动后端（终端 A）：
```powershell
.\infra\scripts\local-backend.ps1 -Action serve
```
2. 启动前端（终端 B）：
```powershell
.\infra\scripts\local-frontend.ps1 -Action dev
```
3. 健康检查（终端 C）：
```powershell
.\infra\scripts\health-check.ps1 -BackendHealthUrl http://localhost:8000/health
```

## 3. 第二轮验收快照（非服务常驻）
1. 前端构建：
```powershell
.\infra\scripts\local-frontend.ps1 -Action build
```
2. 后端关键测试：
```powershell
.\infra\scripts\local-backend.ps1 -Action test -TestScope key
```
可选（包含 API 用例）：
```powershell
.\infra\scripts\local-backend.ps1 -Action test -TestScope key -IncludeApiTests
```
3. 离线评测并生成报告：
```powershell
.\infra\scripts\local-evaluation.ps1 -Dataset qa_demo_v1
```
4. 一键执行上述三步：
```powershell
.\infra\scripts\local-acceptance.ps1 -EvalDataset qa_demo_v1
```
5. 报告查看：
- 默认输出目录：`evaluation/reports/`
- 推荐查看最新 `qa_demo_v1_*.json` 或指定输出文件

## 4. 常见故障排查
1. `npm not found`
- 安装 Node.js LTS，并重开终端验证 `npm -v`。
2. `next build` 报 `spawn EPERM`
- 常见于终端权限/安全软件拦截子进程，建议：
- 以管理员权限打开终端重试
- 关闭占用扫描进程后重试
- 先执行 `npm run dev` 验证开发模式是否可用
3. `Python not found` 或 `pytest/uvicorn` 不可用
- 在 `backend` 下执行：
```powershell
python -m pip install -r requirements.txt
```
4. `preflight` 报缺失变量
- 按 `.env.local-demo.example` 补齐后再重试。
5. `/health` 非 200
- 先确认后端终端是否正常启动，再检查端口是否冲突（默认 `8000`）。
6. 后端 API 测试报缺 `httpx`
- 执行 `python -m pip install httpx` 后重试 `-IncludeApiTests`。
7. 离线评测失败（dataset not found）
- 检查 `evaluation/datasets/<dataset>/manifest.json` 是否存在，或切换 `-Dataset sample_v1`。

## 5. 验收最小操作清单
1. `preflight(all)` 通过
2. 前端 `build` 通过
3. 后端关键测试通过
4. 离线评测产出报告文件
5. 报告中 `release_blocked` 可读且 `gate_results` 有值
