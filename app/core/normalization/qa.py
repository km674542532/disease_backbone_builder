from __future__ import annotations

from collections import Counter
from typing import Dict, List

from app.core.normalization.base import DiseaseNormalizationPayload, NormalizationResult


class NormalizationQACollector:
    def __init__(self) -> None:
        self.gene_results: List[NormalizationResult] = []
        self.disease_results: List[DiseaseNormalizationPayload] = []

    def add_gene(self, result: NormalizationResult) -> None:
        self.gene_results.append(result)

    def add_disease(self, result: DiseaseNormalizationPayload) -> None:
        self.disease_results.append(result)

    def gene_metrics(self) -> Dict[str, int]:
        counter = Counter()
        for result in self.gene_results:
            counter["total_inputs"] += 1
            if result.match_type == "exact":
                counter["exact_match_count"] += 1
            if result.match_type == "alias":
                counter["alias_match_count"] += 1
            if result.match_type == "previous_symbol":
                counter["previous_symbol_match_count"] += 1
            if result.match_type == "fuzzy":
                counter["fuzzy_candidate_count"] += 1
            if "unresolved" in result.qa_flags or result.match_type == "unresolved":
                counter["unresolved_count"] += 1
            if "authority_conflict" in result.qa_flags:
                counter["conflict_count"] += 1
            if "low_confidence" in result.qa_flags:
                counter["low_confidence_count"] += 1
        return {k: int(v) for k, v in counter.items()}

    def disease_metrics(self) -> Dict[str, int]:
        counter = Counter()
        for result in self.disease_results:
            counter["total_inputs"] += 1
            if result.source_authorities_used:
                counter["exact_match_count"] += 1
            if "fuzzy_only" in result.qa_flags:
                counter["fuzzy_candidate_count"] += 1
            if "unresolved" in result.qa_flags:
                counter["unresolved_count"] += 1
            if "authority_conflict" in result.qa_flags:
                counter["conflict_count"] += 1
            if "low_confidence" in result.qa_flags:
                counter["low_confidence_count"] += 1
        return {k: int(v) for k, v in counter.items()}

    def unresolved_items(self) -> List[dict]:
        items = []
        for g in self.gene_results:
            if "unresolved" in g.qa_flags or g.match_type in {"unresolved", "fuzzy"}:
                items.append({"entity_type": "gene", "raw_input": g.raw_input, "qa_flags": g.qa_flags, "candidates": [x.model_dump() for x in g.candidates]})
        for d in self.disease_results:
            if "unresolved" in d.qa_flags:
                items.append({"entity_type": "disease", "raw_input": d.normalized_label, "qa_flags": d.qa_flags})
        return items

    def conflicts(self) -> List[dict]:
        rows = []
        for g in self.gene_results:
            if "authority_conflict" in g.qa_flags or "multiple_candidates" in g.qa_flags:
                rows.append({"entity_type": "gene", "raw_input": g.raw_input, "qa_flags": g.qa_flags, "candidates": [x.model_dump() for x in g.candidates]})
        for d in self.disease_results:
            if "authority_conflict" in d.qa_flags:
                rows.append({"entity_type": "disease", "normalized_label": d.normalized_label, "qa_flags": d.qa_flags, "conflict": d.conflict})
        return rows
