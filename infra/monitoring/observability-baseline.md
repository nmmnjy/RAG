# 日志、监控、告警基线方案

## 1. 日志规范（对齐 00 模块）

统一 JSON 字段：
- `timestamp`
- `level`
- `service`（frontend/backend）
- `env`（dev/test/prod）
- `request_id`
- `trace_id`
- `span_id`
- `user_id`
- `kb_id`
- `doc_id`
- `event`
- `status_code`
- `latency_ms`
- `error_code`
- `safe_message`

脱敏要求：
- 不记录完整 token、密钥、cookie、文档原文。
- `authorization` 等敏感字段按 `LOG_REDACT_FIELDS` 自动脱敏。

## 2. 核心指标
- 可用性：`availability`（SLA 目标 >= 99%）
- 错误率：`5xx_rate`、`4xx_rate`
- 时延：`p50_latency_ms`、`p95_latency_ms`
- 业务指标：`rag_query_success_rate`、`citation_coverage_rate`

## 3. 告警分级
- P1：连续 5 分钟可用性 < 95% 或后端全量不可用。
- P2：`p95_latency_ms > 8000` 持续 10 分钟。
- P3：错误率异常升高（`5xx_rate > 5%` 持续 10 分钟）。

## 4. 告警通道
- 默认：企业 IM 群机器人 + 邮件。
- P1 需额外电话值班通知（主线程接入真实联系人）。
