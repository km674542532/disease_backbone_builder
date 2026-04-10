"""CLI pipeline for building disease backbone draft artifacts."""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.builder_config import BuilderConfig
from app.schemas.disease_descriptor import DiseaseDescriptor, DiseaseIds
from app.services.aggregator import Aggregator
from app.services.assembler import Assembler
from app.services.literature.pubmed_pipeline import run_pubmed_retrieval
from app.services.llm_client import LLMClient, MockLLMClient, QwenAPIClient
from app.services.llm_extractor import LLMExtractor
from app.services.normalizer import Normalizer
from app.services.packetizer import Packetizer
from app.services.pruner import Pruner
from app.services.scorer import Scorer
from app.services.source_collector import SourceCollector
from app.services.validator import Validator
from app.services.backbone_v2 import BackboneV2Refiner
from app.services.v3.source_quality import apply_source_quality, source_tier_distribution
from app.utils.json_io import read_json, write_json, write_jsonl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def _build_llm_client(llm_mode: str, qwen_api_key: Optional[str]) -> LLMClient:
    mode = (llm_mode or "auto").lower()
    env_has_key = bool(os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY"))

    if mode == "mock":
        logger.warning("llm_mode=mock: using MockLLMClient (no external LLM call)")
        return MockLLMClient()

    if mode == "qwen":
        logger.info("llm_mode=qwen: using QwenAPIClient")
        return QwenAPIClient(api_key=qwen_api_key)

    if mode == "auto":
        if qwen_api_key or env_has_key:
            logger.info("llm_mode=auto detected qwen api key: using QwenAPIClient")
            return QwenAPIClient(api_key=qwen_api_key)
        logger.warning("llm_mode=auto without api key: fallback to MockLLMClient")
        return MockLLMClient()

    raise ValueError(f"Unsupported llm_mode={llm_mode}. Use one of: auto, mock, qwen")


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _rule_payload_to_builder_override(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not any(k in payload for k in ("hallmark_rules", "module_rules", "chain_rules", "review_ranking_weights")):
        return payload
    return {
        "aggregation_policy": {
            "min_support_for_core_hallmark": payload.get("hallmark_rules", {}).get("min_support_for_core_hallmark", 2),
            "min_support_for_core_module": payload.get("module_rules", {}).get("min_support_for_core_module", 2),
            "min_chain_confidence": payload.get("chain_rules", {}).get("min_chain_confidence", 0.7),
            "generic_term_filter_enabled": bool(payload.get("module_rules", {}).get("generic_filter_terms", [])),
        },
        "literature_policy": {
            "min_publication_year": payload.get("review_selection_rules", {}).get("min_publication_year", 2018),
            "languages": payload.get("review_selection_rules", {}).get("allowed_languages", ["eng"]),
            "max_selected_reviews": payload.get("review_selection_rules", {}).get("max_selected_reviews", 10),
            "max_selected_systematic_reviews": payload.get("review_selection_rules", {}).get(
                "max_selected_systematic_reviews", 5
            ),
            "max_selected_specialized_reviews": payload.get("review_selection_rules", {}).get(
                "max_selected_specialized_reviews", 8
            ),
        },
        "ranking_policy": {
            "review_type_weight": payload.get("review_ranking_weights", {}).get("review_type_weight", 0.3),
            "recency_weight": payload.get("review_ranking_weights", {}).get("recency_weight", 0.2),
            "impact_factor_weight": payload.get("review_ranking_weights", {}).get("impact_factor_weight", 0.2),
            "mechanism_density_weight": payload.get("review_ranking_weights", {}).get("mechanism_density_weight", 0.2),
            "disease_specificity_weight": payload.get("review_ranking_weights", {}).get("disease_specificity_weight", 0.1),
        },
        "source_weights": payload.get("source_weights", {}),
    }


def _load_builder_config(disease_name: str, config_path: Optional[str]) -> BuilderConfig:
    default_payload = BuilderConfig(disease={"label": disease_name, "mondo_id": "MONDO:UNKNOWN"}).model_dump()
    if not config_path:
        return BuilderConfig.model_validate(default_payload)

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    elif suffix == ".json":
        loaded = read_json(path)
    else:
        raise ValueError(f"Unsupported config file format: {suffix}")

    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a JSON/YAML object")

    override_payload = _rule_payload_to_builder_override(loaded)
    merged = _deep_merge_dict(default_payload, override_payload)
    merged["disease"]["label"] = disease_name
    return BuilderConfig.model_validate(merged)


def _build_artifact_paths(output_root: str, run_id: Optional[str]) -> Dict[str, Path]:
    root = Path(output_root)
    if run_id:
        root = root / run_id
    return {
        "run_root": root,
        "source_packets_jsonl": root / "source_packets" / "source_packets.jsonl",
        "packetization_stats_json": root / "source_packets" / "packetization_stats.json",
        "extraction_results_jsonl": root / "extraction_results" / "extraction_results.jsonl",
        "raw_llm_responses_jsonl": root / "extraction_results" / "raw_llm_responses.jsonl",
        "normalized_candidates_jsonl": root / "aggregation" / "normalized_candidates.jsonl",
        "aggregation_records_json": root / "aggregation" / "aggregation_records.json",
        "scored_items_json": root / "aggregation" / "scored_items.json",
        "prune_log_json": root / "aggregation" / "prune_log.json",
        "backbone_draft_json": root / "outputs" / "disease_backbone_draft.json",
        "backbone_draft_alias_json": root / "outputs" / "pd_backbone_draft_v1_1.json",
        "backbone_draft_v2_json": root / "outputs" / "pd_backbone_draft_v2.json",
        "backbone_draft_v3_json": root / "outputs" / "pd_backbone_draft_v3.json",
        "validation_report_json": root / "outputs" / "validation_report.json",
        "validation_report_v2_json": root / "outputs" / "validation_report_v2.json",
        "validation_report_v3_json": root / "outputs" / "validation_report_v3.json",
        "review_queue_v3_json": root / "outputs" / "review_queue_v3.json",
        "normalization_qa_report_json": root / "outputs" / "normalization_qa_report.json",
        "normalization_unresolved_items_json": root / "outputs" / "normalization_unresolved_items.json",
        "normalization_conflicts_json": root / "outputs" / "normalization_conflicts.json",
        "review_queue_v4_json": root / "outputs" / "review_queue_v4.json",
        "backbone_draft_v4_json": root / "outputs" / "pd_backbone_draft_v4.json",
        "validation_report_v4_json": root / "outputs" / "validation_report_v4.json",
        "backbone_audit_md": Path("docs") / "backbone_audit.md",
        "backbone_review_summary_md": Path("docs") / "backbone_review_summary.md",
        "backbone_v3_gap_analysis_md": Path("docs") / "backbone_v3_gap_analysis.md",
        "normalization_rules_v3_md": Path("docs") / "normalization_rules_v3.md",
        "confidence_scoring_v3_md": Path("docs") / "confidence_scoring_v3.md",
        "backbone_v3_review_summary_md": Path("docs") / "backbone_v3_review_summary.md",
        "normalization_external_sources_gap_analysis_md": Path("docs") / "normalization_external_sources_gap_analysis.md",
        "standard_sources_setup_md": Path("docs") / "standard_sources_setup.md",
        "normalization_rules_externalized_md": Path("docs") / "normalization_rules_externalized.md",
        "review_bundle_dir": root / "outputs" / "review_bundle",
        "effective_config_json": root / "config" / "effective_builder_config.json",
    }


def build(
    input_path: Optional[str],
    disease_name: str,
    *,
    use_pubmed: bool = False,
    max_reviews: int = 50,
    pubmed_email: Optional[str] = None,
    pubmed_api_key: Optional[str] = None,
    pubmed_cache_dir: str = "data/literature_records",
    pubmed_days_back: Optional[int] = None,
    pubmed_query: Optional[str] = None,
    refresh_pubmed: bool = False,
    llm_mode: str = "auto",
    qwen_api_key: Optional[str] = None,
    config_path: Optional[str] = None,
    output_root: str = "data",
    run_id: Optional[str] = None,
) -> None:
    logger.info("stage_start pipeline_build disease=%s", disease_name)
    run_id = run_id or ""
    if not run_id and output_root != "data":
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifacts = _build_artifact_paths(output_root, run_id or None)

    disease = DiseaseDescriptor(label=disease_name, ids=DiseaseIds(mondo="MONDO:UNKNOWN"))
    config = _load_builder_config(disease_name, config_path)
    write_json(artifacts["effective_config_json"], config.model_dump())

    source_files: List[str] = []
    if input_path:
        source_files.append(input_path)

    if use_pubmed:
        try:
            pubmed_jsonl = run_pubmed_retrieval(
                disease=disease_name,
                max_reviews=max_reviews,
                email=pubmed_email,
                api_key=pubmed_api_key,
                cache_dir=pubmed_cache_dir,
                days_back=pubmed_days_back,
                override_query=pubmed_query,
                refresh=refresh_pubmed,
            )
            if pubmed_jsonl:
                source_files.append(pubmed_jsonl)
        except Exception as exc:
            cache_candidate = Path(pubmed_cache_dir) / f"{_slugify(disease_name)}_pubmed.jsonl"
            if input_path:
                logger.warning("pubmed_retrieval_failed_fallback error=%s", exc)
            elif cache_candidate.exists():
                logger.warning("pubmed_retrieval_failed_fallback error=%s using_cache=%s", exc, cache_candidate)
                source_files.append(str(cache_candidate))
            else:
                raise RuntimeError(
                    "PubMed retrieval failed and no local input/cache is available. "
                    f"disease={disease_name} cache={cache_candidate}"
                ) from exc

    if not source_files:
        raise ValueError("No sources available. Provide --input and/or --use-pubmed.")

    collector = SourceCollector()
    packetizer = Packetizer(
        source_packets_path=str(artifacts["source_packets_jsonl"]),
        packetization_stats_path=str(artifacts["packetization_stats_json"]),
    )
    extractor = LLMExtractor(_build_llm_client(llm_mode, qwen_api_key))
    normalizer = Normalizer()
    aggregator = Aggregator()
    scorer = Scorer()
    pruner = Pruner()
    assembler = Assembler()
    validator = Validator()
    refiner = BackboneV2Refiner()

    source_docs = []
    for source_file in source_files:
        source_docs.extend(collector.collect(source_file))
    packets = packetizer.packetize(disease.label, source_docs)
    packet_quality = apply_source_quality(source_docs, packets)

    extraction_results, failed_packets = extractor.extract_packets(
        packets=packets,
        disease_ids=disease.ids.model_dump(),
        seed_genes=disease.seed_genes,
        extraction_results_path=artifacts["extraction_results_jsonl"],
        raw_llm_responses_path=artifacts["raw_llm_responses_jsonl"],
    )
    if failed_packets:
        logger.warning("stage_failed stage=extraction failed_packets=%s", failed_packets)

    normalized = normalizer.normalize(extraction_results)
    write_jsonl(artifacts["normalized_candidates_jsonl"], [n.model_dump() for n in normalized])

    combined, records = aggregator.aggregate(normalized)
    packet_source_type = {p.source_packet_id: p.source_type for p in packets}
    item_confidences = {}
    for key in ("hallmarks", "modules", "chains", "genes"):
        for item in combined.get(key, []):
            norm_key = getattr(item, "normalized_label", getattr(item, "symbol", getattr(item, "title", ""))).lower()
            item_confidences.setdefault(norm_key, []).append(item.candidate_confidence)
    scored_records = scorer.score(records, packet_source_type, item_confidences, config)
    write_json(artifacts["aggregation_records_json"], [x.model_dump() for x in scored_records])
    write_json(artifacts["scored_items_json"], [x.model_dump() for x in scored_records])

    pruned, prune_log = pruner.prune(combined, config)
    write_json(artifacts["prune_log_json"], prune_log)

    refined, review_queue, v3_metrics = refiner.normalize_and_filter_backbone_items(pruned, packet_quality)
    refined["modules"] = refiner.deduplicate_modules(refined.get("modules", []))
    refined["genes"] = refiner.bind_genes_to_modules(refined.get("modules", []), refined.get("genes", []))
    refined["chains"] = refiner.build_canonical_chains(
        refined.get("hallmarks", []), refined.get("modules", []), refined.get("genes", []), refined.get("relations", [])
    )
    disease.ids = DiseaseIds(**refiner.disease_ids_v3(disease.label, disease.ids.model_dump()))

    review_queue_count = sum(len(v) for v in review_queue.values())
    filtered_item_count = sum(1 for m in refined.get("modules", []) if m.status in {"review", "filtered"})
    schema_pass_rate = 1.0 if not extraction_results else round(sum(1 for r in extraction_results if r.extraction_quality.schema_validation_status == "ok") / len(extraction_results), 4)

    draft = assembler.assemble(
        disease,
        config,
        refined,
        packet_source_type,
        review_queue_count=review_queue_count,
        filtered_item_count=filtered_item_count,
        schema_pass_rate=schema_pass_rate,
    )
    draft.backbone_id = "pd_backbone_draft_v3"
    draft.build_quality.source_tier_distribution = source_tier_distribution(packets)
    draft.build_quality.weighted_support_summary = refiner.weighted_support_summary(packet_quality)
    draft.build_quality.promoted_core_item_count = v3_metrics["promoted_core_item_count"]
    draft.build_quality.demoted_low_evidence_item_count = v3_metrics["demoted_low_evidence_item_count"]
    norm_reports = refiner.normalization_reports()
    gene_total = max(1, norm_reports["qa_report"]["gene"].get("total_inputs", 0))
    disease_total = max(1, norm_reports["qa_report"]["disease"].get("total_inputs", 0))
    draft.build_quality.normalized_gene_rate = round(
        (gene_total - norm_reports["qa_report"]["gene"].get("unresolved_count", 0)) / gene_total, 4
    )
    draft.build_quality.normalized_disease_rate = round(
        (disease_total - norm_reports["qa_report"]["disease"].get("unresolved_count", 0)) / disease_total, 4
    )
    draft.build_quality.unresolved_normalization_item_count = len(norm_reports["unresolved_items"])
    draft.build_quality.authority_conflict_count = len(norm_reports["conflicts"])
    write_json(artifacts["backbone_draft_json"], draft.model_dump())
    write_json(artifacts["backbone_draft_alias_json"], draft.model_dump())
    write_json(artifacts["backbone_draft_v2_json"], draft.model_dump())
    write_json(artifacts["backbone_draft_v3_json"], draft.model_dump())
    write_json(artifacts["backbone_draft_v4_json"], draft.model_dump())

    report = validator.validate(draft, config)
    write_json(artifacts["validation_report_json"], report.model_dump())
    write_json(artifacts["validation_report_v2_json"], report.model_dump())
    write_json(artifacts["validation_report_v3_json"], report.model_dump())
    write_json(artifacts["validation_report_v4_json"], report.model_dump())
    review_payload = {k: [x.model_dump() for x in v] for k, v in review_queue.items()}
    review_payload["unresolved_aliases"] = refiner.unresolved_aliases()
    write_json(artifacts["review_queue_v3_json"], review_payload)
    write_json(artifacts["review_queue_v4_json"], review_payload)
    write_json(artifacts["normalization_qa_report_json"], norm_reports["qa_report"])
    write_json(artifacts["normalization_unresolved_items_json"], norm_reports["unresolved_items"])
    write_json(artifacts["normalization_conflicts_json"], norm_reports["conflicts"])

    _write_audit_docs(artifacts, extraction_results, combined, refined, review_queue, prune_log, refiner.unresolved_aliases())

    review_dir = artifacts["review_bundle_dir"]
    review_dir.mkdir(parents=True, exist_ok=True)
    write_json(review_dir / "backbone_summary.json", {
        "backbone_id": draft.backbone_id,
        "hallmark_count": len(draft.hallmarks),
        "module_count": len(draft.modules),
        "chain_count": len(draft.canonical_chains),
        "gene_count": len(draft.key_genes),
    })
    write_json(review_dir / "modules_with_support.json", [
        {
            "candidate_id": m.candidate_id,
            "label": m.label,
            "normalized_label": m.normalized_label,
            "supporting_source_packet_ids": m.supporting_source_packet_ids,
            "snippet": m.description[:200],
            "status": m.status,
        }
        for m in draft.modules
    ])
    write_json(review_dir / "chains_with_support.json", [
        {
            "candidate_id": c.candidate_id,
            "title": c.title,
            "module_label": c.module_label,
            "supporting_source_packet_ids": c.supporting_source_packet_ids,
            "steps": [s.model_dump() for s in c.steps],
            "snippet": " -> ".join(s.event_label for s in c.steps[:3]),
            "status": c.status,
        }
        for c in draft.canonical_chains
    ])
    write_json(review_dir / "review_flags.json", {
        "validation_warnings": report.warnings,
        "review_recommendations": report.review_recommendations,
        "prune_log": prune_log,
    })
    logger.info("stage_end pipeline_build")


def _slugify(value: str) -> str:
    return "_".join(value.lower().strip().split())



def _write_audit_docs(
    artifacts: Dict[str, Path],
    extraction_results: List[Any],
    combined: Dict[str, list],
    refined: Dict[str, list],
    review_queue: Dict[str, list],
    prune_log: List[dict],
    unresolved_aliases: List[str],
) -> None:
    audit_lines = [
        "# Backbone Audit",
        "",
        "- 生成入口: `app/pipelines/build_backbone.py::build`。",
        "- 聚合逻辑: `app/services/aggregator.py::Aggregator.aggregate`。",
        "- schema/validator: `app/schemas/backbone_draft.py` 与 `app/services/validator.py`。",
        "- source packet 处理: `app/services/packetizer.py`, `app/services/llm_extractor.py`, `app/services/normalizer.py`。",
        "",
        "## 粗糙问题结论",
        "- 粗糙项主要来自自由抽取候选直接进入聚合，缺少 seed 约束与噪声过滤。",
        "- hallmark/module 早期缺乏强 schema 限制，导致 unknown 或临床管理类词条混入。",
        "- gene-module / chain 绑定薄弱，导致机制链可解释性不足。",
    ]
    artifacts["backbone_audit_md"].parent.mkdir(parents=True, exist_ok=True)
    artifacts["backbone_audit_md"].write_text("\n".join(audit_lines), encoding="utf-8")

    noise_items = [m.label for m in refined.get("modules", []) if m.status == "review"]
    core_items = [m.label for m in refined.get("modules", []) if m.status == "candidate" and m.module_type == "core_mechanism_module"]
    review_items = [m.label for m in review_queue.get("modules", [])]
    summary_lines = [
        "# Backbone Review Summary",
        "",
        "## 噪声过滤",
        *[f"- {x}" for x in noise_items[:20]],
        "",
        "## 保留核心模块",
        *[f"- {x}" for x in core_items[:20]],
        "",
        "## 仍需人工 review",
        *[f"- {x}" for x in review_items[:20]],
    ]
    artifacts["backbone_review_summary_md"].parent.mkdir(parents=True, exist_ok=True)
    artifacts["backbone_review_summary_md"].write_text("\n".join(summary_lines), encoding="utf-8")
    artifacts["backbone_v3_gap_analysis_md"].write_text(
        "\n".join(
            [
                "# Backbone v3 Gap Analysis",
                "",
                "## 当前 coverage 短板",
                "- v2 中 hallmarks/modules 受 seed 和模板链限制，覆盖不足。",
                "- key_genes 缺少机制绑定导致核心机制稀疏。",
                "",
                "## 当前 normalization 短板",
                "- 基因 alias 未集中治理，SNCA/DJ-1/PINK-1 等存在碎片化。",
                "- phenotype 与 mechanism 混层，导致模块语义不稳定。",
                "",
                "## 当前 chain generation 短板",
                "- v2 使用固定模板链，无法随证据拓展。",
                "- relation edge 未使用 source quality 进行加权。",
                "",
                "## 本轮修复策略",
                "- 引入 source_tier/source_weight 与可解释 confidence breakdown。",
                "- 新增 normalization 子层（gene/disease/mechanism/phenotype）。",
                "- 升级为 graph-based canonical chain builder。",
            ]
        ),
        encoding="utf-8",
    )
    artifacts["normalization_rules_v3_md"].write_text(
        "\n".join(
            [
                "# Normalization Rules v3",
                "",
                "## Gene alias map",
                "- alpha-synuclein / α-synuclein / Α-SYNUCLEIN -> SNCA",
                "- DJ-1 -> PARK7",
                "- PINK-1 -> PINK1",
                "",
                "## Mechanism controlled categories",
                "- alpha_synuclein, mitochondrial, lysosome_autophagy, neuroinflammation, oxidative_stress, synaptic, vesicle_trafficking, proteostasis, metal_homeostasis, gut_brain_axis, dopaminergic_neuron_vulnerability, phenotype, biomarker, intervention",
                "",
                "## Unresolved aliases",
                *[f"- {x}" for x in unresolved_aliases[:50]],
            ]
        ),
        encoding="utf-8",
    )
    artifacts["confidence_scoring_v3_md"].write_text(
        "\n".join(
            [
                "# Confidence Scoring v3",
                "",
                "- confidence = clamp((source_support_score + source_diversity_score + normalization_score + structural_completeness_score + chain_connectivity_score - penalty_score) / 5, 0, 1)",
                "- hallmark/module/gene/relation/chain 全部写入 confidence_breakdown。",
                "- core 条目最低要求：非零 confidence 且满足加权证据门槛。",
            ]
        ),
        encoding="utf-8",
    )
    artifacts["backbone_v3_review_summary_md"].write_text(
        "\n".join(
            [
                "# Backbone v3 Review Summary",
                "",
                "## Hallmarks 保留/合并/降级",
                f"- 保留数量: {len([h for h in refined.get('hallmarks', []) if h.status in {'candidate', 'core-draft'}])}",
                f"- 降级数量: {len([h for h in refined.get('hallmarks', []) if h.status == 'provisional'])}",
                "",
                "## 核心模块",
                *[f"- {m.normalized_label}" for m in refined.get("modules", []) if m.status == "core-draft"][:20],
                "",
                "## 基因绑定",
                *[f"- {g.normalized_symbol or g.symbol}: {', '.join(g.linked_modules[:3])}" for g in refined.get("genes", [])[:20]],
                "",
                "## canonical chains",
                *[f"- {c.title}: {' -> '.join(s.event_label for s in c.steps)}" for c in refined.get("chains", [])[:10]],
                "",
                "## unresolved / low evidence",
                *[f"- {x}" for x in unresolved_aliases[:20]],
            ]
        ),
        encoding="utf-8",
    )
    artifacts["normalization_external_sources_gap_analysis_md"].write_text(
        "\n".join(
            [
                "# Normalization External Sources Gap Analysis",
                "",
                "## 当前实现概况",
                "- 现有流程已接入 HGNC/MONDO/MeSH/Orphanet 离线快照驱动，并保留本地 mechanism/phenotype controlled vocab。",
                "",
                "## 缺失的权威外部源支持",
                "- phenotype 尚未接 HPO；mechanism 尚未接 GO/Reactome；disease 仍缺 OMIM 专用快照。",
                "",
                "## 易误归一/漏归一环节",
                "- 模糊匹配候选在多候选时仅标记冲突，不做上下文判别。",
                "- 新名词若不在快照中会进入 unresolved，需周期更新快照。",
                "",
                "## 本轮修复计划",
                "- 统一 normalization schema + QA 统计闭环 + unresolved/conflict 落盘输出。",
            ]
        ),
        encoding="utf-8",
    )
    artifacts["standard_sources_setup_md"].write_text(
        "\n".join(
            [
                "# Standard Sources Setup",
                "",
                "- HGNC: `data/standards/hgnc/hgnc_complete_set.json`",
                "- MONDO: `data/standards/mondo/mondo_snapshot.json`",
                "- MeSH: `data/standards/mesh/mesh_snapshot.json`",
                "- Orphanet: `data/standards/orphanet/orphanet_snapshot.json`",
                "",
                "支持 JSON（records 列表）格式，推荐包含 `source_version` 与 `snapshot_date`。",
                "更新快照后重新运行 build 命令即可自动加载最新本地快照。",
            ]
        ),
        encoding="utf-8",
    )
    artifacts["normalization_rules_externalized_md"].write_text(
        "\n".join(
            [
                "# Normalization Rules Externalized",
                "",
                "## 已外部化到标准源",
                "- gene: HGNC approved symbol / alias / prev_symbol",
                "- disease: MONDO + MeSH + Orphanet 聚合",
                "",
                "## 仍保留本地规则",
                "- mechanism_category keyword map",
                "- phenotype keyword map",
                "",
                "## 下一步建议",
                "- phenotype 接入 HPO；mechanism 接入 GO + Reactome。",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--disease", required=True)
    parser.add_argument("--use-pubmed", action="store_true")
    parser.add_argument("--max-reviews", type=int, default=50)
    parser.add_argument("--pubmed-email")
    parser.add_argument("--pubmed-api-key")
    parser.add_argument("--pubmed-cache-dir", default="data/literature_records")
    parser.add_argument("--pubmed-days-back", type=int)
    parser.add_argument("--pubmed-query")
    parser.add_argument("--refresh-pubmed", action="store_true")
    parser.add_argument("--llm-mode", choices=["auto", "mock", "qwen"], default="auto")
    parser.add_argument("--qwen-api-key")
    parser.add_argument("--config")
    parser.add_argument("--output-root", default="data")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    build(
        args.input,
        args.disease,
        use_pubmed=args.use_pubmed,
        max_reviews=args.max_reviews,
        pubmed_email=args.pubmed_email,
        pubmed_api_key=args.pubmed_api_key,
        pubmed_cache_dir=args.pubmed_cache_dir,
        pubmed_days_back=args.pubmed_days_back,
        pubmed_query=args.pubmed_query,
        refresh_pubmed=args.refresh_pubmed,
        llm_mode=args.llm_mode,
        qwen_api_key=args.qwen_api_key,
        config_path=args.config,
        output_root=args.output_root,
        run_id=args.run_id,
    )


if __name__ == "__main__":
    main()
