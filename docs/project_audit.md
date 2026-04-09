# Project Audit (Production-Oriented)

## 1) 项目概览

`disease_backbone_builder` 是一个以 **CLI pipeline** 为主入口的疾病机制骨架构建项目，主流程路径为：

1. 读取本地输入源（JSON/JSONL/文本）或抓取 PubMed 综述。
2. 将 source document 切分成 source packet。
3. 调用 LLM（mock 或 Qwen）对每个 packet 做结构化抽取。
4. 做字段标准化与同义词归并。
5. 聚合、打分、裁剪。
6. 组装为 disease backbone draft 并校验。
7. 落盘输出中间与最终 artifacts。

主入口：`python -m app.pipelines.build_backbone ...`（见 `run.sh`）。

---

## 2) 目录结构摘要

> 说明：`build/lib/*` 为构建产物镜像，存在与 `app/*` 重复代码，属于“发布残留”，不应作为开发主线。

- `app/`（核心代码）
  - `pipelines/`：主流程编排（当前唯一主入口）。
  - `services/`：业务服务（抽取、标准化、聚合、评分、裁剪、校验、PubMed 检索等）。
  - `schemas/`：Pydantic 严格 schema（`extra="forbid"`）。
  - `prompts/`：LLM prompt 模板。
  - `utils/`：json io、文本标准化、术语映射。
- `config/`：规则配置（`backbone_rules.v1_1.yaml`），但当前主流程未真正加载使用。
- `data/`：输入、中间结果、输出产物（当前仓库内已包含历史运行结果）。
- `tests/`：schema/service/pipeline 测试。
- `doc/`：框架设计文档（v1.0/v1.1）。
- `docs/`：本次新增审计与 runbook 文档。
- `build/`：构建复制文件（非主线）。

### 核心主线 vs 实验/旁路

**核心主线（被 `build_backbone.py` 直接调用）**
- `source_collector -> packetizer -> llm_extractor -> normalizer -> aggregator -> scorer -> pruner -> assembler -> validator`
- `literature/pubmed_pipeline`（可选输入路径）

**实验/旁路（存在测试但未接入主 pipeline）**
- `review_ranker.py`
- `review_selector.py`
- `source_document_assembler.py`
- `authoritative_source_collector.py`
- `schemas/run_manifest.py`, `schemas/source_manifest.py`, `schemas/artifact_record.py`（定义存在，但主线未驱动）

---

## 3) 主流程调用链（输入 -> 输出）

## 3.1 主入口
- 文件：`app/pipelines/build_backbone.py`
- CLI 参数支持：`--input`, `--disease`, `--use-pubmed`, `--llm-mode`, `--qwen-api-key` 等。

## 3.2 输入源
- 本地输入：`SourceCollector.collect(input_path)` 支持 JSONL/JSON/文本。
- PubMed 输入：`run_pubmed_retrieval(...)` 输出 `data/literature_records/{disease}_pubmed.jsonl`，再进入 `SourceCollector`。

## 3.3 Pipeline 核心链路
1. **collect**：收集原始 source rows。
2. **packetize**：切分为 `SourcePacket`，并写 `data/source_packets/source_packets.jsonl`。
3. **extract**：LLM 抽取为 `ExtractionResult`，同时写：
   - `data/extraction_results/extraction_results.jsonl`
   - `data/extraction_results/raw_llm_responses.jsonl`
4. **normalize**：标准化候选标签、gene symbol、关系字段。
5. **aggregate**：按 normalized key 聚合并生成 aggregation records。
6. **score**：对 aggregation record 评分。
7. **prune**：基于配置裁剪低支持/低质量条目。
8. **assemble**：组装 `DiseaseBackboneDraft`。
9. **validate**：输出 `ValidationReport`。
10. **review bundle**：导出 review 辅助文件。

## 3.4 最终产物
- 主产物：
  - `data/outputs/disease_backbone_draft.json`
  - `data/outputs/pd_backbone_draft_v1_1.json`（同内容双写）
- 校验：`data/outputs/validation_report.json`
- 审阅包：`data/outputs/review_bundle/*`

---

## 4) 核心 Schema 清单与契约审计

## 4.1 主流程关键 schema
- 输入与中间：`SourceDocument`, `SourcePacket`, `ExtractionResult`
- 候选实体：`HallmarkCandidate`, `ModuleCandidate`, `ModuleRelation`, `CausalChainCandidate`, `KeyGeneCandidate`
- 聚合与输出：`BackboneAggregationRecord`, `DiseaseBackboneDraft`, `ValidationReport`
- 配置：`BuilderConfig`（以及未接入主线的 `RuleConfig`）

## 4.2 prompt / LLM 输出 / schema 校验一致性

### 当前做得好的部分
- prompt 明确要求返回固定顶层 keys。
- `ExtractionResult` + `SchemaModel` 全局 `extra="forbid"`，可防止无关字段污染。
- 抽取失败时有 fallback 结构（不会中断整个 pipeline）。

### 结构漂移与风险（schema drift）
1. **status 枚举漂移**
   - prompt 仅允许 `candidate|provisional`。
   - schema `CandidateStatus` 还包含 `core-draft|filtered`。
   - 风险：下游若出现 `core-draft`，prompt 与验证语义不一致。

2. **module_relations 在 scoring 的 item_confidences 中未参与**
   - `build_backbone.py` 中 `item_confidences` 仅遍历 hallmarks/modules/chains/genes。
   - 关系候选评分上下文不对齐，可能影响一致性。

3. **`global_notes` 仅定义为 `List[str]`**
   - 缺少结构化 error code / packet context，后续自动诊断能力弱。

4. **缺少 LLM 输出 normalize/adapter 分层**
   - 当前 LLM 原始 JSON 直接拼接后进入 `ExtractionResult.model_validate(...)`。
   - 若模型字段轻微偏移（如 `module_id`、`confidence` 命名），会直接触发失败；虽有 fallback，但信息损失大。

---

## 5) LLM 调用链审计

## 5.1 调用点
- `LLMExtractor._extract_with_raw` -> `llm_client.generate_json(prompt)`。
- 实现：
  - `MockLLMClient`：离线测试。
  - `QwenAPIClient`：OpenAI SDK 兼容接口调用 DashScope。

## 5.2 输入消息构造
- system：固定“只返回 JSON 对象”。
- user：模板渲染后的 packet prompt，包含 disease ids、seed genes、metadata、source text。

## 5.3 response_format / 重试 / 异常
- `response_format={"type": "json_object"}` 已使用。
- Qwen API 层无显式重试策略（与 PubMedClient 不同），失败直接 RuntimeError。
- 解析失败会记录 raw object 并抛错；extractor 层会回填 failed result。

## 5.4 日志审计
- extraction 层有 stage_started/stage_completed/stage_failed。
- 但 Qwen client 原先使用 `print` 输出调试信息，统一日志可观测性不足（本次已改为 logger）。
- raw response 已有 jsonl 落盘，便于复盘。

## 5.5 核心问题
- 缺少统一 adapter：**LLM输出字段名差异** 与 **schema 强校验** 之间没有缓冲层。
- provider 抽象存在但 extractor 强制 provider=qwen，接口抽象与实现策略不一致。

---

## 6) 配置与依赖审计

## 6.1 依赖声明
- `pyproject.toml` 声明：`pydantic`, `fastapi`, `openai`, `PyYAML`。
- 实际主线 CLI 不依赖 FastAPI（存在“声明与主用途不一致”）。

## 6.2 配置读取
- `BuilderConfig` 在 pipeline 内直接实例化默认值。
- `config/backbone_rules.v1_1.yaml` 与 `RuleConfig` 存在，但主入口未加载。

## 6.3 环境变量
- Qwen：`QWEN_API_KEY` / `DASHSCOPE_API_KEY`（auto mode 检测）。
- PubMed：email/api key 从 CLI 传入，未统一环境变量封装。

## 6.4 可复现性风险
- 仓库包含大量 `data/*` 运行产物，污染“源码仓库”与“运行产物”边界。
- 缺少一次运行的 manifest/run_id 概念，无法清晰追踪多次运行 artifacts。

---

## 7) 数据落盘与产物清单

## 7.1 输入目录
- `data/raw/*`（示例源数据）
- `data/literature_records/*`（PubMed缓存）

## 7.2 中间目录
- `data/source_packets/*`
- `data/extraction_results/*`
- `data/aggregation/*`

## 7.3 输出目录
- `data/outputs/*`
- `data/outputs/review_bundle/*`

## 7.4 发现的问题
- 输出路径写死在服务与pipeline中，缺少统一 output root 注入。
- `packetizer` 与 `pipeline` 双写 `source_packets.jsonl`（重复写）。
- 部分路径策略分散（例如 review selection、source manifest 由旁路模块写到其他目录）。

---

## 8) 可运行性审计

## 8.1 从零启动最短路径（mock）
1. 创建虚拟环境，安装 `pip install -e .[dev]`。
2. 准备最小输入 json/jsonl。
3. 运行：
   - `python -m app.pipelines.build_backbone --input <file> --disease "Parkinson disease" --llm-mode mock`
4. 查看 `data/outputs/disease_backbone_draft.json` 与 `validation_report.json`。

## 8.2 在线路径（PubMed + qwen）
- 需额外提供：`--use-pubmed --pubmed-email ...` 与 `QWEN_API_KEY` 或 `--qwen-api-key`。

## 8.3 当前阻塞项
- 测试环境若未安装 openai 包，导入时会在模块级失败（本次已低风险修复为按需导入，避免 mock 模式被硬阻塞）。

---

## 9) 问题清单与优先级

## P0（阻塞运行/结果错误）
1. **模块级强依赖 openai 导致测试与 mock 流程导入失败**
   - 位置：`app/services/llm_client.py`
   - 表现：未安装 openai 时 pytest collection 直接报错。
   - 根因：顶层导入第三方依赖，未按 provider/运行模式懒加载。
   - 修复：改为 `QwenAPIClient` 内部按需导入 + 统一 logger（已修复）。

2. **缺少 LLM 输出 adapter，schema forbid 下轻微字段漂移即整体失败**
   - 位置：`app/services/llm_extractor.py`
   - 根因：raw JSON 直接进入 `ExtractionResult.model_validate`。
   - 修复建议：增加 `ExtractionAdapter`（字段映射/默认值补齐/枚举归一）再做严格校验。

## P1（结构不清晰/易引入错误）
3. **主线 pipeline 与 review ranking/selection/source manifest 链未打通**
   - 位置：`app/services/review_ranker.py` 等。
   - 根因：存在并行实现路线，缺少统一 orchestrator。
   - 修复建议：在 docs 明确“主线 vs 预备路线”，后续以 feature flag 接入。

4. **配置体系双轨（BuilderConfig vs RuleConfig YAML）未统一**
   - 位置：`app/schemas/builder_config.py`, `app/schemas/rule_config.py`, `config/backbone_rules.v1_1.yaml`
   - 根因：schema 设计与运行时配置注入未收束。
   - 修复建议：以 BuilderConfig 为 runtime 单一入口，YAML 通过 loader merge 进入 BuilderConfig。

## P2（可维护性/文档）
5. **产物路径与命名策略未统一，缺少 run_id artifact 管理**
   - 位置：`app/pipelines/build_backbone.py`, 多个 `write_json*` 调用点。
   - 修复建议：统一 `output_root/run_id/`；保留 latest 软链接或索引。

6. **构建残留 `build/lib` 与源码并存，增加阅读噪音**
   - 修复建议：在文档中标记忽略，并在 `.gitignore`/发布流程中约束。

---

## 10) 最小修复方案（本轮建议）

1. **已做**：修复 `llm_client` 模块级导入问题，提升 mock/test 可运行性。
2. **已做**：新增 `ExtractionAdapter` 并接入 `LLMExtractor`，先做字段别名映射/枚举归一/缺省补齐，再做严格 schema 校验。
3. **已做**：pipeline 支持 `--config`/`--output-root`/`--run-id`，并落盘 `effective_builder_config.json` 作为生效配置快照。
4. **下一步建议**：
   - 扩展 adapter 的 drift 词典（按线上失败样本迭代）。
   - 给 run artifact 增加 index/latest 管理。
