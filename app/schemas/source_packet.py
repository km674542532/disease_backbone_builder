"""Schema for normalized source packets."""
from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

SourceType = Literal[
    "GeneReviews",
    "Orphanet",
    "ReviewArticle",
    "ConsensusStatement",
    "ReactomeSummary",
    "GOSummary",
    "ClinGenSummary",
    "OMIMSummary",
    "Other",
]


class SourceLocator(BaseModel):
    """Locator metadata for a source packet."""

    model_config = ConfigDict(extra="forbid")

    url: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    internal_ref: Optional[str] = None


class SourcePacket(BaseModel):
    """Canonical source packet passed into LLM extraction."""

    model_config = ConfigDict(extra="forbid")

    source_packet_id: str
    disease_label: str
    source_type: SourceType
    source_name: str
    source_title: str
    source_locator: SourceLocator = Field(default_factory=SourceLocator)
    section_label: str
    text_block: str
    metadata: Dict[str, object] = Field(default_factory=dict)
