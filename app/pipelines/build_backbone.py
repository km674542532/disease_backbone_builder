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
        "validation_report_json": root / "outputs" / "validation_report.json",
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

    source_docs = []
    for source_file in source_files:
        source_docs.extend(collector.collect(source_file))
    packets = packetizer.packetize(disease.label, source_docs)

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

    draft = assembler.assemble(disease, config, pruned, packet_source_type)
    write_json(artifacts["backbone_draft_json"], draft.model_dump())
    write_json(artifacts["backbone_draft_alias_json"], draft.model_dump())

    report = validator.validate(draft, config)
    write_json(artifacts["validation_report_json"], report.model_dump())

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
