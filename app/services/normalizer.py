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
    """MVP normalization routines for hallmarks/modules/genes/relations."""

    def normalize(self, extraction_results: List[ExtractionResult]) -> List[ExtractionResult]:
        logger.info("stage_start normalize results=%d", len(extraction_results))
        normalized: List[ExtractionResult] = []
        for result in extraction_results:
            for hallmark in result.hallmarks:
                hallmark.normalized_label = merge_synonym_label(normalize_label(hallmark.label))
            for module in result.modules:
                module.normalized_label = merge_synonym_label(normalize_label(module.label))
                module.key_genes = sorted({map_gene_to_hgnc(normalize_gene_symbol(g)) for g in module.key_genes})
            for gene in result.key_genes:
                gene.symbol = map_gene_to_hgnc(normalize_gene_symbol(gene.symbol))
            for rel in result.module_relations:
                pred = rel.predicate
                if pred not in _ALLOWED_PREDICATES:
                    logger.warning("invalid_predicate source_packet_id=%s predicate=%s", result.source_packet_id, pred)
            normalized.append(result)
        logger.info("stage_end normalize")
        return normalized
