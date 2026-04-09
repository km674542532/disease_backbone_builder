"""CLI pipeline for building disease backbone draft artifacts."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Optional

from app.schemas.builder_config import BuilderConfig
from app.schemas.disease_descriptor import DiseaseDescriptor, DiseaseIds
from app.services.aggregator import Aggregator
from app.services.assembler import Assembler
from app.services.literature.pubmed_pipeline import run_pubmed_retrieval
from app.services.llm_client import MockLLMClient
from app.services.llm_extractor import LLMExtractor
from app.services.normalizer import Normalizer
from app.services.packetizer import Packetizer
from app.services.pruner import Pruner
from app.services.scorer import Scorer
from app.services.source_collector import SourceCollector
from app.services.validator import Validator
from app.utils.json_io import write_json, write_jsonl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


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
) -> None:
    logger.info("stage_start pipeline_build disease=%s", disease_name)
    disease = DiseaseDescriptor(label=disease_name, ids=DiseaseIds(mondo="MONDO:UNKNOWN"))
    config = BuilderConfig(disease={"label": disease_name, "mondo_id": disease.ids.mondo})

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
    packetizer = Packetizer()
    extractor = LLMExtractor(MockLLMClient())
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
    write_jsonl("data/source_packets/source_packets.jsonl", [p.model_dump() for p in packets])

    extraction_results, failed_packets = extractor.extract_packets(
        packets=packets,
        disease_ids=disease.ids.model_dump(),
        seed_genes=disease.seed_genes,
        extraction_results_path="data/extraction_results/extraction_results.jsonl",
        raw_llm_responses_path="data/extraction_results/raw_llm_responses.jsonl",
    )
    if failed_packets:
        logger.warning("stage_failed stage=extraction failed_packets=%s", failed_packets)

    normalized = normalizer.normalize(extraction_results)
    write_jsonl("data/aggregation/normalized_candidates.jsonl", [n.model_dump() for n in normalized])

    combined, records = aggregator.aggregate(normalized)
    packet_source_type = {p.source_packet_id: p.source_type for p in packets}
    item_confidences = {}
    for key in ("hallmarks", "modules", "chains", "genes"):
        for item in combined.get(key, []):
            norm_key = getattr(item, "normalized_label", getattr(item, "symbol", getattr(item, "title", ""))).lower()
            item_confidences.setdefault(norm_key, []).append(item.candidate_confidence)
    scored_records = scorer.score(records, packet_source_type, item_confidences, config)
    write_json("data/aggregation/aggregation_records.json", [x.model_dump() for x in scored_records])
    write_json("data/aggregation/scored_items.json", [x.model_dump() for x in scored_records])

    pruned, prune_log = pruner.prune(combined, config)
    write_json("data/aggregation/prune_log.json", prune_log)

    draft = assembler.assemble(disease, config, pruned, packet_source_type)
    write_json("data/outputs/disease_backbone_draft.json", draft.model_dump())
    write_json("data/outputs/pd_backbone_draft_v1_1.json", draft.model_dump())

    report = validator.validate(draft, config)
    write_json("data/outputs/validation_report.json", report.model_dump())

    review_dir = Path("data/outputs/review_bundle")
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
    )


if __name__ == "__main__":
    main()
