# 评测数据集目录

## 目录约定（V1 骨架）
- `sample_v1/manifest.json`：统一离线评测输入入口（dataset 级）。
- `sample_v1/cases/`：评测 case 数据，按 `OfflineEvaluationCaseInput` 契约组织。
- `sample_v1/expected/`：预留断言快照目录（当前阶段可为空）。
- `sample_v1/snapshots/`：预留中间产物快照目录（当前阶段可为空）。

## 说明
- 当前阶段使用样例数据集 + 规则评测，后续可扩展为真实回放数据。
- 业务字段（`doc_id/kb_id/chunk_id/...`）必须复用 00~05 已冻结命名。
