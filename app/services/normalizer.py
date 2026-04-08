"""Normalize extracted candidates before aggregation."""
from __future__ import annotations

import logging
from typing import List

from app.schemas.candidates import RelationPredicate
from app.schemas.extraction_result import ExtractionResult
from app.utils.ontology_mapper import map_gene_to_hgnc, merge_synonym_label
from app.utils.text_normalize import normalize_gene_symbol, normalize_label

logger = logging.getLogger(__name__)

_ALLOWED_PREDICATES = set(RelationPredicate.__args__)  # type: ignore[attr-defined]


class Normalizer:
    """Normalization of hallmark/module/gene/relation labels with source traceability repair."""

    def normalize(self, extraction_results: List[ExtractionResult]) -> List[ExtractionResult]:
        logger.info("stage_started stage=normalization results=%d", len(extraction_results))
        normalized: List[ExtractionResult] = []
        for result in extraction_results:
            packet_id = result.source_packet_id
            for hallmark in result.hallmarks:
                hallmark.normalized_label = merge_synonym_label(normalize_label(hallmark.label))
                if packet_id not in hallmark.supporting_source_packet_ids:
                    hallmark.supporting_source_packet_ids.append(packet_id)

            for module in result.modules:
                module.normalized_label = merge_synonym_label(normalize_label(module.label))
                module.key_genes = sorted({map_gene_to_hgnc(normalize_gene_symbol(g)) for g in module.key_genes if g})
                module.hallmark_links = [merge_synonym_label(normalize_label(h)) for h in module.hallmark_links]
                if packet_id not in module.supporting_source_packet_ids:
                    module.supporting_source_packet_ids.append(packet_id)

            for gene in result.key_genes:
                gene.symbol = map_gene_to_hgnc(normalize_gene_symbol(gene.symbol))
                gene.linked_modules = [merge_synonym_label(normalize_label(m)) for m in gene.linked_modules]
                if packet_id not in gene.supporting_source_packet_ids:
                    gene.supporting_source_packet_ids.append(packet_id)

            for rel in result.module_relations:
                rel.subject_module = merge_synonym_label(normalize_label(rel.subject_module))
                rel.object_module = merge_synonym_label(normalize_label(rel.object_module))
                if rel.predicate not in _ALLOWED_PREDICATES:
                    logger.warning(
                        "invalid_relation_predicate source_packet_id=%s predicate=%s", packet_id, rel.predicate
                    )
                if packet_id not in rel.supporting_source_packet_ids:
                    rel.supporting_source_packet_ids.append(packet_id)

            for chain in result.causal_chains:
                chain.module_label = merge_synonym_label(normalize_label(chain.module_label))
                if packet_id not in chain.supporting_source_packet_ids:
                    chain.supporting_source_packet_ids.append(packet_id)

            normalized.append(result)
        logger.info("stage_completed stage=normalization")
        return normalized
