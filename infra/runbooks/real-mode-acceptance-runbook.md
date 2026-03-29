# Real-Mode 联调验收手册

## 1. 目标
- 以真实 provider 运行离线评测链路，并输出可审计的 real-mode 验收结果。
- 保持 mock 流程不受影响，real-mode 通过独立脚本触发。

## 2. 环境变量准备
1. 复制并填写：`infra/environments/.env.real-mode.example`
2. 必填重点：
- `EMBEDDING_PROVIDER=openai_compatible`
- `LLM_PROVIDER=openai_compatible`
- `EMBEDDING_PROVIDER_ENABLE_REAL=true`
- `LLM_PROVIDER_ENABLE_REAL=true`
- `EMBEDDING_API_KEY`、`LLM_API_KEY`
- `EMBEDDING_BASE_URL`、`LLM_BASE_URL`
3. 不要在脚本输出或日志中打印密钥。

## 3. 执行顺序
```powershell
.\infra\scripts\local-real-acceptance.ps1 -Environment test -EvalDataset qa_demo_v1 -ForbidFallbackWhenRealMode
```

可选：
- 追加 API 用例：`-IncludeApiTests`

## 4. 验收通过判定
1. `preflight` real mode 通过。
2. 后端关键测试通过。
3. 离线评测报告生成成功。
4. 报告中每个 case 都有 `output_summary.provider_runtime`，且包含 `embedding` 与 `llm` 字段。
5. `gate_real_mode_forbid_fallback` 存在，且行为可解释：
- 若启用 `-ForbidFallbackWhenRealMode`：
  - `passed=true` 表示 real 模式未发生 fallback。
  - `passed=false` 表示检测到 fallback，按门禁阻断。
- 若未启用：
  - 通常为 `passed=true` 且 `metric_value=skipped_not_enforced`。

## 5. 常见问题
1. `preflight` 报 real mode 校验失败
- 检查 provider 类型、`*_ENABLE_REAL`、`*_BASE_URL`、`*_API_KEY`。
2. 报告无 `provider_runtime`
- 检查是否使用了 `local-real-acceptance.ps1` 或 `local-evaluation.ps1 -RealMode`。
3. `gate_real_mode_forbid_fallback` 失败
- 说明 real 模式发生 fallback；优先检查 provider 可达性、密钥权限、超时配置。
