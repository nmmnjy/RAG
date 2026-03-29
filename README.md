# 企业知识库智能问答系统（RAG）- V1 冻结可用版

本仓库当前处于 **V1 可用版冻结状态**，已完成 `00~08` 模块验收，可用于本地启动、演示与后续迭代恢复。

## 项目概览
- 架构：RAG（文档解析 -> 语义分块 -> 向量化存储 -> 混合检索 -> 答案生成与溯源）
- 前端：Next.js + Tailwind CSS v4
- 后端：FastAPI
- 评测与验收：`infra/scripts/local-acceptance.ps1` + 离线评测报告
- 统一问答接口：`POST /api/v1/qa/answers`

## 环境要求
- 操作系统：Windows（当前脚本以 PowerShell 为主）
- Python：3.11+
- Node.js：20+
- npm：10+

建议端口：
- 后端：`8000`
- 前端：`3000`

## 快速启动（完整步骤）
在仓库根目录 `D:\Projects\RAG` 执行。

### 1) 安装后端依赖
```powershell
cd backend
pip install -r requirements.txt
```

### 2) 安装前端依赖
```powershell
cd ..\frontend
npm install
```

### 3) 配置环境变量
- 后端参考：`backend/.env.example`
- 前端参考：`frontend/.env.example`
- 运维模板参考：`infra/environments/README.md`

### 4) 启动后端
```powershell
cd ..\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5) 启动前端（新开一个终端）
```powershell
cd D:\Projects\RAG\frontend
npm run dev
```

### 6) 一键验收（可选但推荐）
```powershell
cd D:\Projects\RAG
powershell -ExecutionPolicy Bypass -File .\infra\scripts\local-acceptance.ps1 -EvalDataset qa_demo_v1
```

## 最小验证清单（先看效果）
1. 打开前端：`http://localhost:3000/qa`
2. 输入 `kb_id` 和问题后提交，确认页面有可见状态变化（`loading -> answered/refused/failed`）。
3. 查看结果区是否返回以下字段：
   - `answer`
   - `citations`
   - `confidence`
   - `refuse_reason`
4. 若有引用，点击引用详情跳转到 `/citations/[citationId]` 页面。
5. 访问管理页验证可见性：
   - `http://localhost:3000/admin/documents`
   - `http://localhost:3000/admin/tasks`
   - `http://localhost:3000/admin/logs`

## 常见问题快速排查
### 1) 提问后“没反应”
- 打开浏览器开发者工具看网络请求，确认是否调用 `POST /api/v1/qa/answers`。
- 检查后端是否启动在 `8000` 端口。
- 检查前端环境变量中的后端地址是否正确。

### 2) 页面出现 `404`（如 `/admin/docs`）
- 当前管理路由是 `/admin/documents`，不是 `/admin/docs`。

### 3) 请求超时或 `RETR_TIMEOUT`
- 降低 `top_k`、`vector_top_k`、`keyword_top_k`。
- 确认后端未阻塞，优先执行一次 `local-acceptance` 看整体健康状态。

### 4) `spawn EPERM` / 权限相关报错
- 在受限环境下可能出现进程拉起失败，可用提权方式执行测试/构建。
- 优先使用 `infra/scripts` 中的一键脚本，减少手工命令差异。

## 相关文档
- 任务总览：`docs/README_任务分发总览.md`
- 冻结后路线图：`docs/ROADMAP_FREEZE.md`
- 部署与运维：`docs/specs/08_部署与运维.md`
