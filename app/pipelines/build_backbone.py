"""CLI pipeline for building disease backbone draft artifacts."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.schemas.builder_config import BuilderConfig
from app.schemas.disease_descriptor import DiseaseDescriptor, DiseaseIds
from app.services.aggregator import Aggregator
from app.services.assembler import Assembler
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


def build(input_path: str, disease_name: str) -> None:
    logger.info("stage_start pipeline_build disease=%s", disease_name)
    disease = DiseaseDescriptor(label=disease_name, ids=DiseaseIds(mondo="MONDO:UNKNOWN"))
    config = BuilderConfig(disease={"label": disease_name, "mondo_id": disease.ids.mondo})

    collector = SourceCollector()
    packetizer = Packetizer()
    extractor = LLMExtractor(MockLLMClient())
    normalizer = Normalizer()
    aggregator = Aggregator()
    scorer = Scorer()
    pruner = Pruner()
    assembler = Assembler()
    validator = Validator()

    source_docs = collector.collect(input_path)
    packets = packetizer.packetize(disease.label, source_docs)
    write_jsonl("data/source_packets/source_packets.jsonl", [p.model_dump() for p in packets])

    extraction_results = []
    for packet in packets:
        try:
            res = extractor.extract(packet, disease.ids.model_dump(), disease.seed_genes)
            extraction_results.append(res)
        except Exception:
            logger.exception("failed_extraction source_packet_id=%s", packet.source_packet_id)
    write_jsonl("data/extraction_results/extraction_results.jsonl", [r.model_dump() for r in extraction_results])

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

    report = validator.validate(draft)
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--disease", required=True)
    args = parser.parse_args()
    build(args.input, args.disease)


if __name__ == "__main__":
    main()
