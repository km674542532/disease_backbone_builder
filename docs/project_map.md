# Project Map

## 模块职责总览

| 模块 | 职责 | 关键文件 | 主要输入 | 主要输出 |
|---|---|---|---|---|
| Pipeline | 编排主流程 | `app/pipelines/build_backbone.py` | CLI 参数、source 文件、可选 PubMed | 全量 artifacts |
| Source Ingestion | 读取本地 JSON/JSONL/文本 | `app/services/source_collector.py` | 本地路径 | source rows(dict) |
| PubMed Retrieval | 检索并缓存 PubMed 记录 | `app/services/literature/pubmed_pipeline.py`, `app/services/pubmed_client.py` | disease/query/email | pubmed jsonl/meta/raw |
| Packetization | 文档切分为 source packets | `app/services/packetizer.py` | source rows / SourceDocument | `SourcePacket[]` + stats |
| LLM Extraction | packet 级结构化抽取 | `app/services/llm_extractor.py`, `app/services/llm_client.py`, `app/prompts/packet_extraction.txt` | SourcePacket + disease上下文 | `ExtractionResult[]` + raw responses |
| Normalization | 标签、基因符号、关系字段归一 | `app/services/normalizer.py`, `app/utils/text_normalize.py`, `app/utils/ontology_mapper.py` | ExtractionResult[] | normalized ExtractionResult[] |
| Aggregation | 同义项聚合 + 证据合并 | `app/services/aggregator.py` | normalized results | combined candidates + aggregation records |
| Scoring & Pruning | 支持度打分与裁剪 | `app/services/scorer.py`, `app/services/pruner.py` | aggregation records + config | scored/pruned candidates |
| Assembly | 组装最终草案 | `app/services/assembler.py` | disease/config/pruned items | DiseaseBackboneDraft |
| Validation | 规则校验与提醒 | `app/services/validator.py` | draft/config | ValidationReport |

## Schema 分层图

- 基础层：`SchemaModel`（`extra="forbid"`）
- 输入层：`SourceDocument`, `SourcePacket`
- 抽取层：`ExtractionResult` + candidate schemas
- 聚合层：`BackboneAggregationRecord`
- 输出层：`DiseaseBackboneDraft`, `ValidationReport`
- 配置层：`BuilderConfig` / `RuleConfig`（当前双轨）

## 主线调用简图

```text
CLI(build_backbone)
  -> SourceCollector / run_pubmed_retrieval
  -> Packetizer
  -> LLMExtractor(LLMClient)
  -> Normalizer
  -> Aggregator
  -> Scorer
  -> Pruner
  -> Assembler
  -> Validator
  -> write artifacts(data/...)
```

## 预备链路（未接入主线）

- `ReviewRanker` + `ReviewSelector` + `SourceDocumentAssembler`
- `authoritative_source_collector`
- manifest 类 schema（`RunManifest`, `SourceManifest`, `ArtifactRecord`）

建议：在接入前明确 feature flag 与产物协议，避免主线和实验线混杂。
