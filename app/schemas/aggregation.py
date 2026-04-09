"""Schemas for aggregated backbone candidates."""
from __future__ import annotations

from typing import List

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import SchemaModel
from app.schemas.enums import ModuleRecordType


class BackboneAggregationRecord(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    aggregation_id: str
    item_type: ModuleRecordType
    normalized_key: str
    merged_labels: List[str] = Field(default_factory=list)
    source_count: int = 0
    source_packet_ids: List[str] = Field(default_factory=list)
    source_document_ids: List[str] = Field(default_factory=list)
    merged_key_genes: List[str] = Field(default_factory=list)
    merged_process_terms: List[str] = Field(default_factory=list)
    support_score: float = 0.0
    review_flags: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_support_score(self) -> "BackboneAggregationRecord":
        if not (0.0 <= self.support_score <= 1.0):
            raise ValueError("support_score must be within 0-1")
        return self
