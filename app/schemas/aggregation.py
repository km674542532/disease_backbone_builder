"""Schemas for aggregated backbone candidates."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, ConfigDict


class BackboneAggregationRecord(BaseModel):
    """Intermediate merged record for one normalized key."""

    model_config = ConfigDict(extra="forbid")

    aggregation_id: str
    item_type: Literal["hallmark", "module", "chain", "gene", "relation"]
    normalized_key: str
    merged_labels: List[str] = Field(default_factory=list)
    source_count: int = 0
    source_packet_ids: List[str] = Field(default_factory=list)
    merged_key_genes: List[str] = Field(default_factory=list)
    merged_process_terms: List[str] = Field(default_factory=list)
    support_score: float = 0.0
    review_flags: List[str] = Field(default_factory=list)
