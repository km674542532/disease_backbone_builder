"""Score aggregated records with MVP support heuristics."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from app.schemas.aggregation import BackboneAggregationRecord
from app.schemas.builder_config import BuilderConfig


class Scorer:
    """Computes support score for aggregation records."""

    def score(
        self,
        records: List[BackboneAggregationRecord],
        normalized_results_source_types: Dict[str, str],
        item_confidences: Dict[str, List[float]],
        config: BuilderConfig,
    ) -> List[BackboneAggregationRecord]:
        for rec in records:
            source_types = [normalized_results_source_types.get(sid, "Other") for sid in rec.source_packet_ids]
            diversity = len(set(source_types)) / max(1, len(config.source_weights))
            auth = 0.0
            if source_types:
                auth = sum(config.source_weights.get(st, 0.5) for st in source_types) / len(source_types)
            mean_conf = sum(item_confidences.get(rec.normalized_key, [0.5])) / max(1, len(item_confidences.get(rec.normalized_key, [0.5])))
            specificity = 0.2 if any(term in rec.normalized_key for term in ["stress", "inflammation", "metabolism"]) else 1.0
            rec.support_score = round(0.45 * diversity + 0.25 * auth + 0.20 * mean_conf + 0.10 * specificity, 4)
        return records
