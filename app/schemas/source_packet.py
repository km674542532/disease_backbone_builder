"""Schema for normalized source packets."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import ConfigDict, Field

from app.schemas.base import SchemaModel
from app.schemas.enums import ReviewBucket, SourceType


class SourcePacket(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    source_packet_id: str
    source_document_id: str = ""
    disease_label: str
    source_type: SourceType
    source_name: str
    source_title: str
    section_label: str
    text_block: str
    source_priority_tier: ReviewBucket = "supplementary_review"
    selection_metadata: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
