# Refactor TODO

## P0（必须优先）

- [ ] 增加 LLM 输出适配层（adapter/normalizer before schema validate）。
  - 文件：`app/services/llm_extractor.py`（新增 `app/services/extraction_adapter.py`）
  - 动作：
    - 对字段别名做映射（如 `module_id -> candidate_id` 等）
    - 枚举值归一（status/predicate/gene_role）
    - 缺省字段补齐（supporting ids / warnings）
    - adapter 后再 `ExtractionResult.model_validate`

- [ ] 统一 LLM 错误可观测性，输出结构化错误上下文。
  - 文件：`app/services/llm_client.py`, `app/services/llm_extractor.py`
  - 动作：
    - request id / source_packet_id 贯穿
    - raw response 摘要与异常类型一致记录

## P1（结构清晰化）

- [ ] 统一配置入口，收束 `BuilderConfig` 与 `RuleConfig` 双轨。
  - 文件：`app/pipelines/build_backbone.py`, `app/schemas/builder_config.py`, `app/schemas/rule_config.py`, `config/backbone_rules.v1_1.yaml`
  - 动作：
    - pipeline 支持 `--config`
    - YAML -> BuilderConfig merge
    - 标注最终生效配置快照落盘

- [ ] 将“实验链路”与“主线链路”隔离。
  - 文件：`app/services/review_ranker.py`, `app/services/review_selector.py`, `app/services/source_document_assembler.py`, `docs/project_map.md`
  - 动作：
    - 标记 experimental 包路径或 feature flag
    - 明确接入点与产物 contract

- [ ] 引入运行级 artifact 管理（run_id/output_root）。
  - 文件：`app/pipelines/build_backbone.py`, `app/utils/json_io.py`
  - 动作：
    - 所有输出改写入 `data/runs/{run_id}/...`
    - latest 软链接/索引（可选）

## P2（维护性提升）

- [ ] 清理/隔离 `build/lib` 复制代码，避免阅读混淆。
  - 文件：`build/lib/**`（流程层面）
  - 动作：
    - 通过打包流程生成而非入库
    - 在贡献指南中注明忽略

- [ ] 统一字段命名策略文档（candidate_id/module_label 等）。
  - 文件：`docs/project_audit.md`, `docs/project_map.md`
  - 动作：
    - 增补“字段命名约定”节

- [ ] 为 pipeline 增加 `--dry-run` 与 `--stage`（可选）。
  - 文件：`app/pipelines/build_backbone.py`
  - 动作：
    - 支持按阶段运行，便于调试

- [ ] 建立 README 首页最小运行说明并链接 runbook。
  - 文件：`README.md`（若后续补充）
