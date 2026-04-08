# Disease Backbone Builder

## 完整 schema + pipeline 文档 v1.1

---

## 1. 定位

> **Disease Backbone Builder v1.1 = 一个把权威疾病资料与自动发现的高价值综述转成“初步 disease mechanism backbone draft” 的自动化构建器。**

它的目标仍然不是直接生成最终真值 disease map，而是生成一个**可追溯、可审阅、可扩展**的 backbone draft。这个定位与 v1 一致：输出应始终是 `draft / candidate / provisional`，而不是最终真值；每个对象都必须挂 source；builder 先做 disease-level backbone，不直接做全量扩图 。

### 1.1 核心输出

* disease hallmarks
* core mechanism modules
* module relations
* canonical causal chains
* key genes
* source support
* review selection / provenance
* validation + review package

### 1.2 v1.1 的新增重点

相较 v1，v1.1 新增三块能力：

1. **Authoritative sources 与 review literature 分层**
2. **PubMed API 自动检索 review / systematic review**
3. **impact factor 作为 review ranking 的辅助因子，而不是唯一阈值**

---

## 2. 顶层架构

你原始版本的主线是：
Input disease → Source collection → packetization → LLM extraction → aggregation → normalization → scoring/pruning → assembly → validation → export，这条线是对的 。
v1.1 把 Source collection 拆得更清楚：

```text
Input disease
  ↓
Disease initialization
  ↓
Authoritative source collection
  ↓
PubMed review discovery
  ↓
Review normalization and deduplication
  ↓
Review ranking and triage
  ↓
Source manifest freeze
  ↓
Source packetization
  ↓
LLM constrained extraction
  ↓
Normalization and ontology mapping
  ↓
Candidate aggregation
  ↓
Scoring and pruning
  ↓
Backbone assembly
  ↓
Validation
  ↓
Review package export
```

---

## 3. 输入与输出

### 3.1 输入

```json
{
  "disease_name": "Parkinson disease",
  "disease_ids": {
    "mondo": "MONDO:0005180",
    "mesh": "D010300",
    "orphanet": null,
    "omim": null
  },
  "optional_seed_genes": ["PRKN", "PINK1", "LRRK2", "GBA", "SNCA", "VPS35"],
  "builder_config": "...",
  "runtime_policies": "..."
}
```

### 3.2 输出

延续你 v1 的输出结构，并增加 literature 相关中间件：

* `disease_backbone_draft.json`
* `source_manifest.json`
* `literature_queries.json`
* `literature_records.jsonl`
* `review_selection.jsonl`
* `source_packets.jsonl`
* `extraction_results.jsonl`
* `aggregation_records.json`
* `prune_log.json`
* `validation_report.json`
* `review_bundle/`

---

## 4. 核心设计原则

这些原则直接继承你 v1 的工程约束，并做少量扩展 。

### 4.1 不生成最终真值

所有对象只能处于：

* candidate
* provisional
* core-draft

不能写成 truth / final truth / gold truth。

### 4.2 每个对象都必须可追溯

每个 hallmark、module、relation、chain、gene 都必须回连到：

* source packet
* source document
* literature selection record（若来自 review）

### 4.3 先 disease backbone，后扩图

builder 聚焦 disease-level causal scaffold，不直接承担全量通路重建。

### 4.4 优先可审阅，而不是一步到位

你的原版已经强调 review bundle，这一点保留不变 。

### 4.5 authoritative sources 优先于 review literature

GeneReviews / Orphanet / ClinGen / OMIM summary 是锚点。review 用于补充、细化、校正，不取代锚点。

### 4.6 IF 只作为 ranking factor

impact factor 只能参与排序，不可单独决定保留或丢弃。

---

## 5. 完整 schema 设计 v1.1

在你原来的 10 个核心对象基础上，扩展到 14 个：

1. BuilderConfig
2. DiseaseDescriptor
3. LiteratureQueryPlan
4. LiteratureRecord
5. ReviewSelectionRecord
6. SourceDocument
7. SourcePacket
8. ExtractionResult
9. HallmarkCandidate
10. ModuleCandidate
11. CausalChainCandidate
12. BackboneAggregationRecord
13. DiseaseBackboneDraft
14. ValidationReport

---

## 5.1 BuilderConfig

这是 v1 的扩展版。你原本已经有 `source_policy / llm_policy / aggregation_policy / output_policy`，现在新增 `literature_policy / ranking_policy` 。

```json
{
  "builder_id": "disease_backbone_builder_v1_1",
  "version": "1.1.0",
  "disease": {
    "label": "Parkinson disease",
    "mondo_id": "MONDO:0005180",
    "mesh_id": "D010300",
    "orphanet_id": null
  },
  "source_policy": {
    "preferred_source_types": [
      "GeneReviews",
      "Orphanet",
      "ClinGenSummary",
      "OMIMSummary",
      "ReviewArticle",
      "SystematicReview",
      "ReactomeSummary",
      "GOSummary"
    ],
    "max_documents_per_source_type": 20,
    "max_packets_per_source": 30,
    "max_text_chars_per_packet": 12000
  },
  "literature_policy": {
    "enable_pubmed_review_discovery": true,
    "max_pubmed_candidates": 200,
    "min_publication_year": 2018,
    "languages": ["eng"],
    "publication_types": ["Review"],
    "allow_systematic_review_subset": true,
    "max_selected_reviews": 10,
    "max_selected_systematic_reviews": 5,
    "max_selected_specialized_reviews": 8
  },
  "llm_policy": {
    "provider": "qwen",
    "mode": "json_constrained_extraction",
    "temperature": 0.1,
    "allow_world_knowledge": false,
    "require_source_grounding": true,
    "emit_raw_response": true
  },
  "aggregation_policy": {
    "min_support_for_core_module": 2,
    "min_support_for_core_hallmark": 2,
    "min_chain_confidence": 0.7,
    "generic_term_filter_enabled": true
  },
  "ranking_policy": {
    "use_impact_factor": true,
    "impact_factor_weight": 0.2,
    "recency_weight": 0.2,
    "review_type_weight": 0.3,
    "mechanism_density_weight": 0.2,
    "disease_specificity_weight": 0.1
  },
  "output_policy": {
    "emit_review_flags": true,
    "emit_provisional_items": true,
    "formats": ["json", "jsonl", "csv"]
  }
}
```

---

## 5.2 DiseaseDescriptor

保留 v1 主体，只补一个 `scope_policy`。

```json
{
  "label": "Parkinson disease",
  "synonyms": ["Parkinson's disease", "PD"],
  "ids": {
    "mondo": "MONDO:0005180",
    "mesh": "D010300",
    "orphanet": null,
    "omim": null
  },
  "seed_genes": ["PRKN", "PINK1", "LRRK2", "GBA", "SNCA", "VPS35"],
  "disease_scope_note": "Build a disease-level mechanistic backbone, not full phenome coverage.",
  "scope_policy": {
    "prefer_disease_central_mechanisms": true,
    "allow_supporting_modules": true,
    "allow_peripheral_modules": true,
    "full_graph_expansion_in_scope": false
  }
}
```

---

## 5.3 LiteratureQueryPlan

这是 v1.1 新增对象。

```json
{
  "query_id": "litq_pd_001",
  "disease_label": "Parkinson disease",
  "query_family": "review_discovery",
  "query_string": "(Parkinson Disease[MeSH Terms] OR parkinson*[Title/Abstract]) AND review[Publication Type]",
  "date_range": {
    "start_year": 2018,
    "end_year": 2026
  },
  "language_filter": ["eng"],
  "max_results": 200,
  "priority": 1,
  "notes": "disease-level mechanism reviews"
}
```

建议同一疾病至少生成 3 类 query：

* disease-level review
* systematic review
* mechanism-focused review

---

## 5.4 LiteratureRecord

```json
{
  "literature_id": "pmid_12345678",
  "pmid": "12345678",
  "doi": "10.xxxx/xxxx",
  "title": "Molecular mechanisms of Parkinson disease",
  "journal": "Nature Reviews Neurology",
  "publication_year": 2024,
  "abstract": "...",
  "authors": ["..."],
  "publication_types": ["Review"],
  "mesh_terms": ["Parkinson Disease", "Mitochondria"],
  "language": "eng",
  "pubmed_url": "...",
  "retrieval_query_id": "litq_pd_001",
  "retrieval_source": "pubmed_api",
  "is_review_like": true
}
```

---

## 5.5 ReviewSelectionRecord

```json
{
  "selection_id": "rsel_001",
  "pmid": "12345678",
  "journal": "Nature Reviews Neurology",
  "publication_year": 2024,
  "review_bucket": "anchor_review",
  "impact_factor": 28.1,
  "impact_factor_source": "third_party_package",
  "review_rank_score": 0.91,
  "mechanism_density_score": 0.88,
  "disease_specificity_score": 0.94,
  "decision": "selected",
  "reasons": [
    "high-quality review",
    "disease-centric",
    "mechanism-rich abstract",
    "recent publication"
  ],
  "flags": []
}
```

### review_bucket 受控词表

* anchor_review
* systematic_review
* specialized_review
* supplementary_review
* rejected

---

## 5.6 SourceDocument

这个对象把 authoritative summary 和 selected review 统一起来。

```json
{
  "source_document_id": "src_pd_rev_001",
  "disease_label": "Parkinson disease",
  "source_type": "ReviewArticle",
  "source_name": "PubMedReview",
  "source_title": "Molecular mechanisms of Parkinson disease",
  "source_locator": {
    "pmid": "12345678",
    "doi": "10.xxxx/xxxx",
    "url": null,
    "internal_ref": null
  },
  "priority_tier": "anchor_review",
  "selection_metadata": {
    "review_rank_score": 0.91,
    "impact_factor": 28.1
  },
  "metadata": {
    "publication_year": 2024,
    "is_review_like": true,
    "is_authoritative_summary": false,
    "language": "en"
  }
}
```

---

## 5.7 SourcePacket

你原 schema 已经是对的，v1.1 只加 review provenance 字段 。

```json
{
  "source_packet_id": "sp_rev_pd_001_03",
  "source_document_id": "src_pd_rev_001",
  "disease_label": "Parkinson disease",
  "source_type": "ReviewArticle",
  "source_name": "PubMedReview",
  "source_title": "Molecular mechanisms of Parkinson disease",
  "section_label": "Pathogenesis",
  "text_block": "...",
  "source_priority_tier": "anchor_review",
  "selection_metadata": {
    "review_rank_score": 0.91,
    "review_bucket": "anchor_review"
  },
  "metadata": {
    "publication_year": 2024,
    "language": "en"
  }
}
```

---

## 5.8 ExtractionResult

保留 v1 主体。

```json
{
  "source_packet_id": "sp_rev_pd_001_03",
  "disease": {
    "label": "Parkinson disease",
    "mondo_id": "MONDO:0005180"
  },
  "hallmarks": [],
  "modules": [],
  "module_relations": [],
  "causal_chains": [],
  "key_genes": [],
  "global_notes": [],
  "extraction_quality": {
    "llm_confidence": 0.87,
    "needs_manual_review": false,
    "warnings": [],
    "parse_status": "ok",
    "schema_validation_status": "ok"
  }
}
```

---

## 5.9 HallmarkCandidate

```json
{
  "candidate_id": "hallmark_cand_001",
  "label": "mitochondrial dysfunction",
  "normalized_label": "mitochondrial dysfunction",
  "description": "Mitochondrial homeostasis impairment is a central pathogenic theme.",
  "evidence_scope": "disease_level",
  "supporting_source_packet_ids": ["sp_gr_pd_001", "sp_rev_pd_001_03"],
  "supporting_source_document_ids": ["src_gr_pd_001", "src_pd_rev_001"],
  "supporting_spans": [],
  "candidate_confidence": 0.93,
  "status": "candidate"
}
```

---

## 5.10 ModuleCandidate

```json
{
  "candidate_id": "module_cand_001",
  "label": "PINK1-PRKN mediated mitophagy",
  "normalized_label": "mitophagy",
  "description": "Damage sensing and selective removal of impaired mitochondria.",
  "module_type": "core_mechanism_module",
  "hallmark_links": ["mitochondrial dysfunction"],
  "key_genes": ["PINK1", "PRKN", "FBXO7"],
  "process_terms": [
    "PINK1 stabilization",
    "PRKN recruitment",
    "mitochondrial protein ubiquitination",
    "mitophagy initiation"
  ],
  "supporting_source_packet_ids": ["sp_gr_pd_001", "sp_rev_pd_001_03"],
  "candidate_confidence": 0.92,
  "status": "candidate"
}
```

---

## 5.11 CausalChainCandidate

```json
{
  "candidate_id": "chain_cand_001",
  "title": "Mitophagy failure drives neuronal vulnerability",
  "module_label": "mitophagy",
  "steps": [
    {"order": 1, "event_label": "mitochondrial depolarization"},
    {"order": 2, "event_label": "PINK1 stabilization on damaged mitochondria"},
    {"order": 3, "event_label": "PRKN recruitment"},
    {"order": 4, "event_label": "mitochondrial protein ubiquitination"},
    {"order": 5, "event_label": "mitophagy initiation"},
    {"order": 6, "event_label": "damaged mitochondria clearance failure"},
    {"order": 7, "event_label": "dopaminergic neuron vulnerability"}
  ],
  "trigger_examples": ["PINK1 loss", "PRKN loss"],
  "supporting_source_packet_ids": ["sp_gr_pd_001", "sp_rev_pd_001_03"],
  "candidate_confidence": 0.9,
  "status": "candidate"
}
```

---

## 5.12 BackboneAggregationRecord

延续 v1。

```json
{
  "aggregation_id": "agg_mod_001",
  "item_type": "module",
  "normalized_key": "mitophagy",
  "merged_labels": [
    "PINK1-PRKN mediated mitophagy",
    "mitophagy",
    "selective mitochondrial autophagy"
  ],
  "source_count": 3,
  "source_packet_ids": ["sp_gr_pd_001", "sp_orpha_pd_001", "sp_rev_pd_001_03"],
  "source_document_ids": ["src_gr_pd_001", "src_orpha_pd_001", "src_pd_rev_001"],
  "merged_key_genes": ["PINK1", "PRKN", "FBXO7"],
  "merged_process_terms": [
    "PINK1 stabilization",
    "PRKN recruitment",
    "mitophagy initiation"
  ],
  "support_score": 0.91,
  "review_flags": []
}
```

---

## 5.13 DiseaseBackboneDraft

你原来已有这个最终对象，我这里扩了 literature summary 字段 。

```json
{
  "backbone_id": "pd_backbone_draft_v1_1",
  "builder_version": "1.1.0",
  "disease": {
    "label": "Parkinson disease",
    "ids": {
      "mondo": "MONDO:0005180",
      "mesh": "D010300"
    }
  },
  "hallmarks": [],
  "modules": [],
  "module_relations": [],
  "canonical_chains": [],
  "key_genes": [],
  "source_summary": {
    "source_document_count": 10,
    "source_packet_count": 36,
    "source_type_counts": {
      "GeneReviews": 1,
      "Orphanet": 1,
      "ReviewArticle": 6,
      "SystematicReview": 2
    }
  },
  "literature_summary": {
    "pubmed_candidate_count": 124,
    "selected_review_count": 8,
    "selected_systematic_review_count": 2,
    "selected_specialized_review_count": 3
  },
  "build_quality": {
    "overall_confidence": 0.88,
    "items_needing_review": 3,
    "provisional_item_count": 5
  },
  "status": "draft"
}
```

---

## 5.14 ValidationReport

延续 v1，并加 literature coverage。

```json
{
  "backbone_id": "pd_backbone_draft_v1_1",
  "validation_passed": true,
  "checks": {
    "hallmark_count_ok": true,
    "module_count_ok": true,
    "all_core_modules_have_support": true,
    "all_chains_have_multiple_steps": true,
    "all_key_genes_linked_to_module": true,
    "generic_module_filter_passed": true,
    "literature_manifest_present": true
  },
  "warnings": [
    "Module 'cell stress response' is too generic and remains provisional."
  ],
  "review_recommendations": [
    "Review relationship between lysosomal dysfunction and alpha-synuclein aggregation."
  ]
}
```

---

## 6. Review 文献分层策略

这是 v1.1 的核心新增。

### 6.1 source tier

* **Tier A: authoritative summaries**

  * GeneReviews
  * Orphanet
  * ClinGen summary
  * OMIM summary

* **Tier B: anchor reviews**

  * 高质量、疾病中心、机制丰富的 review

* **Tier C: systematic reviews**

  * 系统综述 / consensus-like reviews

* **Tier D: specialized reviews**

  * 专注某一模块，如 mitophagy / lysosome / proteostasis

* **Tier E: supplementary**

  * 支持度较弱但可作为补充的综述

### 6.2 review bucket 规则

**anchor_review**

* disease-specific
* mechanism-rich
* recent
* journal quality较高

**systematic_review**

* systematic / evidence synthesis 优先保留

**specialized_review**

* 子模块价值高，即使 IF 一般也保留

**rejected**

* 太泛
* 非疾病中心
* abstract 机制密度太低
* 重复度太高

---

## 7. Review ranking 规则

### 7.1 最终排序公式

```text
review_rank_score =
  0.30 * review_type_score +
  0.20 * recency_score +
  0.20 * impact_factor_score +
  0.20 * mechanism_density_score +
  0.10 * disease_specificity_score
```

### 7.2 各项定义

**review_type_score**

* systematic review: 1.0
* disease-specific review: 0.9
* specialized mechanism review: 0.8
* broad review: 0.5

**recency_score**

* ≤3 years: 1.0
* 4–5 years: 0.8
* 6–8 years: 0.6
* older: 0.3

**impact_factor_score**

* 归一化到 0–1
* 仅辅助排序，不是硬阈值

**mechanism_density_score**
abstract / title 中机制词密度：

* pathogenesis
* mechanism
* molecular mechanism
* pathway
* mitophagy
* lysosomal
* proteostasis
* mitochondrial
* neurodegeneration
* trafficking

**disease_specificity_score**

* 直接聚焦目标疾病：高
* 泛神经退行性疾病综述：中
* 过泛综述：低

---

## 8. Source packetization 规则

你原文里已经明确 source packet 要按 `section / subsection / paragraph group` 切，而不是机械 token 切分，这点继续保留 。

### 8.1 packet 切分原则

* 优先按标题与小节边界切
* 优先保留 disease mechanism / pathogenesis / molecular basis 段落
* 避免跨主题拼接
* 每个 packet 尽量机制语义完整

### 8.2 packet metadata 必须保留

* source_document_id
* source_type
* source_title
* section_label
* text_block
* disease_label
* priority_tier
* review bucket / IF / selection score（若来自 review）

---

## 9. LLM constrained extraction

你原版已经定义了 packet 级 constrained extraction，这块不需要推翻，只做 v1.1 兼容 。

### 9.1 抽取原则

* 只能使用 packet 显式支持的信息
* 不允许外部常识补全
* 优先抽 disease-relevant mechanisms
* generic / weak items 标 provisional 或省略
* 输出 JSON only

### 9.2 结果对象

* hallmarks
* modules
* module_relations
* causal_chains
* key_genes
* global_notes
* extraction_quality

---

## 10. Normalization

你原版已把 normalization 放在 extraction 之后，这里保留，并稍作扩展 。

### 10.1 hallmark normalization

* lowercase
* 去停用词
* 同义短语归并

### 10.2 module normalization

* canonical module label
* 长标题压缩为标准模块名
* process terms 规范化

### 10.3 gene normalization

* HGNC symbol
* 去重
* alias 合并

### 10.4 relation normalization

* 映射到 controlled vocab：

  * upstream_of
  * downstream_of
  * interacts_with
  * converges_on
  * amplifies
  * impairs
  * supports
  * linked_to

---

## 11. Aggregation

这部分与 v1 一致，是 backbone 质量的关键层 。

### 11.1 hallmark 聚合

* 合并同义主题
* 统计 source diversity
* 检查是否 disease-central

### 11.2 module 聚合

* 合并等价模块
* 保留可独立扩展的机制块
* 泛化模块降级或丢弃

### 11.3 causal chain 聚合

* 至少 3 步
* 有序事件链
* module 内可解释
* 起点终点语义明确

### 11.4 gene-role 聚合

* core_driver
* major_associated_gene
* module_specific_gene
* supporting_gene
* uncertain

---

## 12. Scoring and pruning

你原版已经有 source weights 与 support_score 逻辑，我这里升级成 v1.1 版 。

### 12.1 support score

```text
support_score =
  0.30 * source_diversity_score +
  0.20 * authoritative_anchor_score +
  0.20 * review_quality_score +
  0.20 * mean_llm_confidence +
  0.10 * disease_specificity_score
```

### 12.2 解释

**source_diversity_score**
不同 source type 越多越高

**authoritative_anchor_score**
是否被 GeneReviews / Orphanet / ClinGen / OMIM 锚定

**review_quality_score**
来自 selected reviews 的综合质量

**mean_llm_confidence**
抽取置信度均值

**disease_specificity_score**
是否真正是 disease-central mechanism

### 12.3 pruning 规则

保留为 **core**

* support_score 高
* 机制边界明确
* 非泛化
* disease-specificity 足够

保留为 **provisional**

* 有潜力但支持不足
* 文献支持不够稳定
* 模块边界尚不清楚

丢弃

* 过泛
* 支持弱
* 与 disease 关联差

---

## 13. 完整 pipeline 设计 v1.1

---

### Stage 0：Disease initialization

输入：

* disease_name
* disease_ids
* seed_genes
* builder_config

输出：

* `disease_descriptor.json`
* run_id
* workspace 目录

---

### Stage 1A：Authoritative source collection

收集：

* GeneReviews
* Orphanet
* ClinGen summary
* OMIM summary

输出：

* `authoritative_sources.json`

---

### Stage 1B：PubMed review discovery

自动生成 query plan：

* disease-level reviews
* systematic reviews
* mechanism-focused reviews

输出：

* `literature_queries.json`

---

### Stage 1C：Review retrieval

从 PubMed 拉取：

* PMID
* title
* abstract
* journal
* year
* publication type
* DOI

输出：

* `literature_records.jsonl`

---

### Stage 1D：Review normalization and deduplication

处理：

* PMID 去重
* DOI 去重
* publication type 规范化
* language 过滤
* year 过滤

输出：

* `literature_records_dedup.jsonl`

---

### Stage 1E：Review ranking and triage

计算：

* review_type_score
* recency_score
* impact_factor_score
* mechanism_density_score
* disease_specificity_score
* review_rank_score

并输出 bucket：

* anchor_review
* systematic_review
* specialized_review
* supplementary_review
* rejected

输出：

* `review_selection.jsonl`

---

### Stage 1F：Source manifest freeze

冻结本次运行实际使用的 source documents。

输出：

* `source_manifest.json`

---

### Stage 2：Source packetization

你原版这里已经很清晰，保留不变：按 section / subsection / paragraph group 切分 。

输出：

* `source_packets.jsonl`

---

### Stage 3：LLM constrained extraction

对每个 packet 抽取：

* hallmarks
* modules
* relations
* chains
* genes

并记录：

* raw response
* parse status
* schema validation

输出：

* `extraction_results.jsonl`

---

### Stage 4：Normalization

输出：

* `normalized_candidates.jsonl`

---

### Stage 5：Aggregation

输出：

* `aggregation_records.json`

---

### Stage 6：Scoring and pruning

输出：

* `scored_items.json`
* `prune_log.json`

---

### Stage 7：Backbone assembly

组装为：

* hallmarks
* modules
* module_relations
* canonical_chains
* key_genes
* literature summary
* build quality

输出：

* `disease_backbone_draft.json`

---

### Stage 8：Validation

你原版验证项继续保留：hallmark 数量、module 数量、chain steps、gene-module linkage、generic filter 等 。

新增：

* literature manifest 是否存在
* 是否至少有 1 个 authoritative source
* 是否至少有 1 个 selected review

输出：

* `validation_report.json`

---

### Stage 9：Review package export

继续保留 review bundle，用于人工快速审阅 。

内容包括：

* backbone draft
* 每个 module 的 supporting snippets
* 每个 hallmark 的 supporting packets
* selected review list
* low-confidence / provisional items
* review flags

输出：

* `review_bundle/`

---

## 14. 目录结构建议 v1.1

你原目录结构是合理的，我在 schemas / services / pipelines 里补 literature 相关模块即可 。

```text
disease_backbone_builder/
├─ app/
│  ├─ schemas/
│  │  ├─ builder_config.py
│  │  ├─ disease_descriptor.py
│  │  ├─ literature_query_plan.py
│  │  ├─ literature_record.py
│  │  ├─ review_selection_record.py
│  │  ├─ source_document.py
│  │  ├─ source_packet.py
│  │  ├─ extraction_result.py
│  │  ├─ candidates.py
│  │  ├─ aggregation.py
│  │  ├─ backbone_draft.py
│  │  └─ validation_report.py
│  ├─ prompts/
│  │  ├─ packet_extraction.txt
│  │  ├─ module_refinement.txt
│  │  └─ merge_assist.txt
│  ├─ services/
│  │  ├─ authoritative_source_collector.py
│  │  ├─ pubmed_client.py
│  │  ├─ review_query_builder.py
│  │  ├─ literature_normalizer.py
│  │  ├─ review_ranker.py
│  │  ├─ review_selector.py
│  │  ├─ packetizer.py
│  │  ├─ llm_extractor.py
│  │  ├─ normalizer.py
│  │  ├─ aggregator.py
│  │  ├─ scorer.py
│  │  ├─ pruner.py
│  │  ├─ assembler.py
│  │  └─ validator.py
│  ├─ pipelines/
│  │  ├─ retrieve_reviews.py
│  │  └─ build_backbone.py
│  └─ utils/
│     ├─ text_normalize.py
│     ├─ ontology_mapper.py
│     ├─ impact_factor_lookup.py
│     └─ json_io.py
├─ data/
│  ├─ literature_queries/
│  ├─ literature_records/
│  ├─ review_selection/
│  ├─ raw_sources/
│  ├─ source_packets/
│  ├─ extraction_results/
│  ├─ aggregation/
│  ├─ outputs/
│  └─ review_bundle/
└─ tests/
```

---

## 15. 最小可用规则配置 v1.1

这是在你原 YAML 规则基础上的升级版 。

```yaml
hallmark:
  min_core_support_count: 2
  max_count: 8

module:
  min_core_support_count: 2
  max_count: 12
  generic_filter_terms:
    - stress
    - apoptosis
    - inflammation
    - metabolism
    - signaling abnormality

chain:
  min_steps: 3
  min_confidence: 0.7

gene:
  min_confidence_for_core_driver: 0.8

source_weights:
  GeneReviews: 1.0
  Orphanet: 0.9
  ClinGenSummary: 0.9
  OMIMSummary: 0.8
  ReviewArticle: 0.8
  SystematicReview: 0.85
  ReactomeSummary: 0.7
  GOSummary: 0.6

review_selection:
  min_year: 2018
  max_selected_reviews: 10
  max_selected_systematic_reviews: 5
  max_selected_specialized_reviews: 8

review_ranking_weights:
  review_type: 0.30
  recency: 0.20
  impact_factor: 0.20
  mechanism_density: 0.20
  disease_specificity: 0.10
```

---

## 16. PD 上的预期输出 v1.1

你原文已经给了 PD backbone draft 的雏形；v1.1 只是在这个结果里增加 literature summary 和更完整的 provenance，而核心内容仍是 hallmarks / modules / chains / genes 。

```json
{
  "backbone_id": "pd_backbone_draft_v1_1",
  "disease": {
    "label": "Parkinson disease",
    "ids": {
      "mondo": "MONDO:0005180",
      "mesh": "D010300"
    }
  },
  "hallmarks": [
    {
      "label": "mitochondrial dysfunction",
      "support_score": 0.94,
      "source_count": 4,
      "status": "core"
    },
    {
      "label": "impaired mitophagy and autophagy",
      "support_score": 0.92,
      "source_count": 4,
      "status": "core"
    }
  ],
  "modules": [
    {
      "label": "mitophagy",
      "description": "Selective clearance of damaged mitochondria.",
      "key_genes": ["PINK1", "PRKN", "FBXO7"],
      "support_score": 0.93,
      "status": "core"
    },
    {
      "label": "lysosomal dysfunction",
      "description": "Impaired lysosomal degradation and endolysosomal homeostasis.",
      "key_genes": ["GBA", "ATP13A2", "VPS35"],
      "support_score": 0.87,
      "status": "core"
    }
  ],
  "canonical_chains": [
    {
      "title": "PINK1-PRKN failure impairs damaged mitochondria clearance",
      "module_label": "mitophagy",
      "support_score": 0.90,
      "status": "core"
    }
  ],
  "key_genes": [
    {
      "symbol": "PRKN",
      "gene_role": "core_driver",
      "linked_modules": ["mitophagy"]
    }
  ],
  "literature_summary": {
    "pubmed_candidate_count": 124,
    "selected_review_count": 8,
    "selected_systematic_review_count": 2
  }
}
```

---

## 17. v1.1 的一句话总结

> **Disease Backbone Builder v1.1 = 用 authoritative disease summaries 作为锚点，用 PubMed 自动发现高价值 review 作为补充，通过 constrained LLM extraction + programmatic normalization / aggregation / pruning，生成一个可追溯、可审阅、可扩展的 disease mechanism backbone draft。**

---

