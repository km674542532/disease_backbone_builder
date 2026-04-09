"""Review ranking service for triage decisions."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from app.schemas.disease_descriptor import DiseaseDescriptor
from app.schemas.literature_record import LiteratureRecord

logger = logging.getLogger(__name__)


class ReviewRanker:
    def __init__(self, impact_factor_lookup: Optional[Callable[[str], Optional[float]]] = None) -> None:
        self.impact_factor_lookup = impact_factor_lookup or (lambda _journal: None)

    @staticmethod
    def _review_type_score(record: LiteratureRecord) -> float:
        types = {x.lower() for x in record.publication_types}
        text = f"{record.title} {record.abstract}".lower()
        if "systematic review" in types or "meta-analysis" in types:
            return 1.0
        if "parkinson" in text and "review" in types:
            return 0.9
        mechanism_terms = ["mechanism", "pathogenesis", "pathway", "mitochond", "lysosom", "proteostasis"]
        if any(t in text for t in mechanism_terms):
            return 0.8
        return 0.5

    @staticmethod
    def _recency_score(publication_year: int) -> float:
        age = datetime.now(timezone.utc).year - publication_year
        if age <= 3:
            return 1.0
        if age <= 5:
            return 0.8
        if age <= 8:
            return 0.6
        return 0.3

    @staticmethod
    def _impact_factor_score(impact_factor: Optional[float]) -> float:
        if impact_factor is None:
            return 0.4
        return max(0.0, min(1.0, impact_factor / 20.0))

    @staticmethod
    def _mechanism_density_score(record: LiteratureRecord) -> float:
        mechanism_terms = [
            "pathogenesis", "mechanism", "molecular mechanism", "pathway", "mitophagy",
            "lysosomal", "proteostasis", "mitochondrial", "neurodegeneration", "trafficking",
        ]
        text = f"{record.title} {record.abstract}".lower()
        if not text.strip():
            return 0.0
        matches = sum(text.count(term) for term in mechanism_terms)
        token_count = max(1, len(text.split()))
        density = min(1.0, matches / max(5, token_count * 0.03))
        return round(density, 4)

    @staticmethod
    def _disease_specificity_score(record: LiteratureRecord, disease: DiseaseDescriptor) -> float:
        text = f"{record.title} {record.abstract}".lower()
        disease_terms = [disease.label.lower(), *(s.lower() for s in disease.synonyms)]
        if any(t in text for t in disease_terms):
            return 1.0
        if "neurodegenerative" in text or "parkinsonism" in text:
            return 0.6
        return 0.3

    def rank(self, records: List[LiteratureRecord], disease: DiseaseDescriptor) -> List[Dict[str, object]]:
        logger.info("audit stage=review_ranking_triage status=started disease=%s records=%d", disease.label, len(records))
        ranked: List[Dict[str, object]] = []
        for rec in records:
            impact_factor = self.impact_factor_lookup(rec.journal)
            review_type_score = self._review_type_score(rec)
            recency_score = self._recency_score(rec.publication_year)
            impact_factor_score = self._impact_factor_score(impact_factor)
            mechanism_density_score = self._mechanism_density_score(rec)
            disease_specificity_score = self._disease_specificity_score(rec, disease)
            final_score = (
                0.30 * review_type_score
                + 0.20 * recency_score
                + 0.20 * impact_factor_score
                + 0.20 * mechanism_density_score
                + 0.10 * disease_specificity_score
            )
            ranked.append(
                {
                    "record": rec,
                    "review_type_score": round(review_type_score, 4),
                    "recency_score": round(recency_score, 4),
                    "impact_factor": impact_factor,
                    "impact_factor_source": "third_party_package" if impact_factor is not None else None,
                    "impact_factor_score": round(impact_factor_score, 4),
                    "mechanism_density_score": round(mechanism_density_score, 4),
                    "disease_specificity_score": round(disease_specificity_score, 4),
                    "review_rank_score": round(final_score, 4),
                }
            )
        ranked.sort(
            key=lambda x: (
                x["review_rank_score"],
                x["disease_specificity_score"],
                x["mechanism_density_score"],
            ),
            reverse=True,
        )
        logger.info("audit stage=review_ranking_triage status=completed disease=%s ranked=%d", disease.label, len(ranked))
        return ranked
