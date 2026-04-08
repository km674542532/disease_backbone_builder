"""Build PubMed review-discovery query plans for diseases."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from app.schemas.disease_descriptor import DiseaseDescriptor
from app.schemas.literature_query_plan import LiteratureQueryPlan, QueryDateRange

logger = logging.getLogger(__name__)


class ReviewQueryBuilder:
    """Generate extensible PubMed query plans from DiseaseDescriptor."""

    def __init__(self, default_max_results: int = 50, lookback_years: int = 15) -> None:
        self.default_max_results = default_max_results
        self.lookback_years = lookback_years

    def build(self, disease: DiseaseDescriptor) -> List[LiteratureQueryPlan]:
        logger.info("audit stage=pubmed_review_discovery.query_builder status=started disease=%s", disease.label)
        current_year = datetime.now(timezone.utc).year
        date_range = QueryDateRange(start_year=current_year - self.lookback_years, end_year=current_year)

        disease_terms = [disease.label, *disease.synonyms]
        disease_clause = " OR ".join(f'"{term}"[Title/Abstract]' for term in disease_terms if term.strip())

        mesh_clause = ""
        if disease.ids.mesh:
            mesh_clause = f' OR "{disease.ids.mesh}"[MeSH Terms]'

        base = f"({disease_clause}{mesh_clause})"

        plans = [
            LiteratureQueryPlan(
                query_id=f"{disease.label.lower().replace(' ', '_')}_review",
                disease_label=disease.label,
                query_family="review_discovery",
                query_string=f"{base} AND review[Publication Type]",
                date_range=date_range,
                language_filter=["eng"],
                max_results=self.default_max_results,
                priority=1,
                notes="Disease-level review discovery.",
            ),
            LiteratureQueryPlan(
                query_id=f"{disease.label.lower().replace(' ', '_')}_systematic",
                disease_label=disease.label,
                query_family="systematic_review_discovery",
                query_string=f"{base} AND review[Publication Type] AND systematic[sb]",
                date_range=date_range,
                language_filter=["eng"],
                max_results=self.default_max_results,
                priority=2,
                notes="Systematic review-focused discovery.",
            ),
            LiteratureQueryPlan(
                query_id=f"{disease.label.lower().replace(' ', '_')}_mechanism",
                disease_label=disease.label,
                query_family="mechanism_review_discovery",
                query_string=(
                    f"{base} AND (mechanism[Title/Abstract] OR pathogenesis[Title/Abstract] "
                    f"OR pathway[Title/Abstract]) AND review[Publication Type]"
                ),
                date_range=date_range,
                language_filter=["eng"],
                max_results=self.default_max_results,
                priority=3,
                notes="Mechanism/pathogenesis/pathway focused review discovery.",
            ),
        ]
        logger.info("audit stage=pubmed_review_discovery.query_builder status=completed disease=%s queries=%d", disease.label, len(plans))
        return plans
