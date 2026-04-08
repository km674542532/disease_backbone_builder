"""Aggregate normalized candidates across source packets."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Tuple

from app.schemas.aggregation import BackboneAggregationRecord
from app.schemas.extraction_result import ExtractionResult

logger = logging.getLogger(__name__)


class Aggregator:
    """Merge by normalized labels and compute support counts."""

    def aggregate(self, normalized_results: List[ExtractionResult]) -> Tuple[Dict[str, list], List[BackboneAggregationRecord]]:
        logger.info("stage_start aggregate results=%d", len(normalized_results))
        hallmarks = defaultdict(list)
        modules = defaultdict(list)
        chains = defaultdict(list)
        genes = defaultdict(list)

        for result in normalized_results:
            for h in result.hallmarks:
                hallmarks[h.normalized_label].append(h)
            for m in result.modules:
                modules[m.normalized_label].append(m)
            for c in result.causal_chains:
                chains[f"{c.module_label}:{c.title.lower()}"] .append(c)
            for g in result.key_genes:
                genes[g.symbol].append(g)

        records: List[BackboneAggregationRecord] = []
        combined = {"hallmarks": [], "modules": [], "chains": [], "genes": []}

        def make_record(kind: str, key: str, items: list, index: int) -> BackboneAggregationRecord:
            source_ids = sorted({sid for it in items for sid in getattr(it, "supporting_source_packet_ids", [])})
            labels = sorted({getattr(it, "label", getattr(it, "symbol", key)) for it in items})
            genes_merged = sorted({kg for it in items for kg in getattr(it, "key_genes", [])})
            process_merged = sorted({pt for it in items for pt in getattr(it, "process_terms", [])})
            return BackboneAggregationRecord(
                aggregation_id=f"agg_{kind}_{index:04d}",
                item_type=kind,
                normalized_key=key,
                merged_labels=labels,
                source_count=len(source_ids),
                source_packet_ids=source_ids,
                merged_key_genes=genes_merged,
                merged_process_terms=process_merged,
                support_score=0.0,
                review_flags=[],
            )

        for i, (key, items) in enumerate(hallmarks.items(), start=1):
            combined["hallmarks"].append(max(items, key=lambda x: x.candidate_confidence))
            records.append(make_record("hallmark", key, items, i))
        for i, (key, items) in enumerate(modules.items(), start=1):
            combined["modules"].append(max(items, key=lambda x: x.candidate_confidence))
            records.append(make_record("module", key, items, i))
        for i, (key, items) in enumerate(chains.items(), start=1):
            combined["chains"].append(max(items, key=lambda x: x.candidate_confidence))
            records.append(make_record("chain", key, items, i))
        for i, (key, items) in enumerate(genes.items(), start=1):
            combined["genes"].append(max(items, key=lambda x: x.candidate_confidence))
            records.append(make_record("gene", key, items, i))

        logger.info("stage_end aggregate records=%d", len(records))
        return combined, records
