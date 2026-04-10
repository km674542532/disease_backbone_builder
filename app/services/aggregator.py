"""Aggregate normalized candidates across source packets."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Tuple

from app.schemas.aggregation import BackboneAggregationRecord
from app.schemas.extraction_result import ExtractionResult
from app.utils.ontology_mapper import merge_synonym_label
from app.utils.text_normalize import normalize_label

logger = logging.getLogger(__name__)


class Aggregator:
    """Merge synonymous hallmark/module/chain/gene/relation candidates with support accounting."""

    def aggregate(self, normalized_results: List[ExtractionResult]) -> Tuple[Dict[str, list], List[BackboneAggregationRecord]]:
        logger.info("stage_started stage=aggregation results=%d", len(normalized_results))
        hallmarks = defaultdict(list)
        modules = defaultdict(list)
        chains = defaultdict(list)
        genes = defaultdict(list)
        relations = defaultdict(list)

        for result in normalized_results:
            for h in result.hallmarks:
                key = merge_synonym_label(normalize_label(h.normalized_label or h.label))
                hallmarks[key].append(h)
            for m in result.modules:
                key = merge_synonym_label(normalize_label(m.normalized_label or m.label))
                modules[key].append(m)
            for c in result.causal_chains:
                module_key = merge_synonym_label(normalize_label(c.module_label))
                step_key = " -> ".join(step.event_label.strip().lower() for step in c.steps)
                chains[f"{module_key}::{step_key}"] .append(c)
            for g in result.key_genes:
                genes[g.symbol.upper()].append(g)
            for r in result.module_relations:
                sub = merge_synonym_label(normalize_label(r.subject_module))
                obj = merge_synonym_label(normalize_label(r.object_module))
                relations[f"{sub}|{r.predicate}|{obj}"].append(r)

        records: List[BackboneAggregationRecord] = []
        combined = {"hallmarks": [], "modules": [], "chains": [], "genes": [], "relations": []}

        def make_record(kind: str, key: str, items: list, index: int) -> BackboneAggregationRecord:
            source_packet_ids = sorted({sid for it in items for sid in getattr(it, "supporting_source_packet_ids", [])})
            source_document_ids = sorted({sid for it in items for sid in getattr(it, "supporting_source_document_ids", [])})
            labels = sorted({getattr(it, "label", getattr(it, "symbol", key)) for it in items})
            genes_merged = sorted({kg for it in items for kg in getattr(it, "key_genes", [])})
            process_merged = sorted({pt for it in items for pt in getattr(it, "process_terms", [])})
            return BackboneAggregationRecord(
                aggregation_id=f"agg_{kind}_{index:04d}",
                item_type=kind,
                normalized_key=key,
                merged_labels=labels,
                source_count=len(source_packet_ids),
                source_packet_ids=source_packet_ids,
                source_document_ids=source_document_ids,
                merged_key_genes=genes_merged,
                merged_process_terms=process_merged,
                support_score=0.0,
                review_flags=[],
            )

        for i, (key, items) in enumerate(sorted(hallmarks.items()), start=1):
            exemplar = max(items, key=lambda x: x.candidate_confidence)
            exemplar.supporting_source_packet_ids = sorted({sid for it in items for sid in it.supporting_source_packet_ids})
            exemplar.supporting_source_document_ids = sorted({sid for it in items for sid in it.supporting_source_document_ids})
            combined["hallmarks"].append(exemplar)
            records.append(make_record("hallmark", key, items, i))

        for i, (key, items) in enumerate(sorted(modules.items()), start=1):
            exemplar = max(items, key=lambda x: x.candidate_confidence)
            exemplar.supporting_source_packet_ids = sorted({sid for it in items for sid in it.supporting_source_packet_ids})
            exemplar.supporting_source_document_ids = sorted({sid for it in items for sid in it.supporting_source_document_ids})
            exemplar.key_genes = sorted({g for it in items for g in it.key_genes})
            exemplar.process_terms = sorted({p for it in items for p in it.process_terms})
            exemplar.evidence_count = sum(max(1, len(it.supporting_source_packet_ids)) for it in items)
            combined["modules"].append(exemplar)
            records.append(make_record("module", key, items, i))

        for i, (key, items) in enumerate(sorted(chains.items()), start=1):
            exemplar = max(items, key=lambda x: x.candidate_confidence)
            exemplar.supporting_source_packet_ids = sorted({sid for it in items for sid in it.supporting_source_packet_ids})
            exemplar.supporting_source_document_ids = sorted({sid for it in items for sid in it.supporting_source_document_ids})
            combined["chains"].append(exemplar)
            records.append(make_record("chain", key, items, i))

        for i, (key, items) in enumerate(sorted(genes.items()), start=1):
            exemplar = max(items, key=lambda x: x.candidate_confidence)
            exemplar.supporting_source_packet_ids = sorted({sid for it in items for sid in it.supporting_source_packet_ids})
            exemplar.supporting_source_document_ids = sorted({sid for it in items for sid in it.supporting_source_document_ids})
            exemplar.linked_modules = sorted({m for it in items for m in it.linked_modules})
            combined["genes"].append(exemplar)
            records.append(make_record("gene", key, items, i))

        for i, (key, items) in enumerate(sorted(relations.items()), start=1):
            exemplar = max(items, key=lambda x: x.candidate_confidence)
            exemplar.supporting_source_packet_ids = sorted({sid for it in items for sid in it.supporting_source_packet_ids})
            exemplar.supporting_source_document_ids = sorted({sid for it in items for sid in it.supporting_source_document_ids})
            combined["relations"].append(exemplar)
            records.append(make_record("relation", key, items, i))

        logger.info("stage_completed stage=aggregation records=%d", len(records))
        return combined, records
