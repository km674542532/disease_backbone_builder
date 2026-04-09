"""Score aggregated records with MVP support heuristics."""
from __future__ import annotations

from typing import Dict, List

from app.schemas.aggregation import BackboneAggregationRecord
from app.schemas.builder_config import BuilderConfig


class Scorer:
    """Compute support_score based on support breadth, source authority, and confidence."""

    def score(
        self,
        records: List[BackboneAggregationRecord],
        normalized_results_source_types: Dict[str, str],
        item_confidences: Dict[str, List[float]],
        config: BuilderConfig,
    ) -> List[BackboneAggregationRecord]:
        source_weight_total = max(sum(config.source_weights.values()), 0.0001)
        for rec in records:
            source_types = [normalized_results_source_types.get(packet_id, "Other") for packet_id in rec.source_packet_ids]
            if source_types:
                authority_score = sum(config.source_weights.get(source_type, 0.5) for source_type in source_types) / len(source_types)
            else:
                authority_score = 0.0
            authority_score = min(1.0, authority_score)

            support_score = min(1.0, rec.source_count / 4.0)
            diversity_score = min(1.0, len(set(source_types)) / 3.0)
            confs = item_confidences.get(rec.normalized_key, [0.5])
            confidence_score = sum(confs) / len(confs)
            weighted_authority = min(1.0, authority_score / max(source_weight_total / max(len(config.source_weights), 1), 0.0001))

            rec.support_score = round(
                0.35 * support_score + 0.25 * diversity_score + 0.25 * confidence_score + 0.15 * weighted_authority,
                4,
            )
        return records
