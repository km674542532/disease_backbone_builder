"""Final disease backbone draft schema."""
from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.candidates import (
    CausalChainCandidate,
    HallmarkCandidate,
    KeyGeneCandidate,
    ModuleCandidate,
    ModuleRelation,
)


class DraftDiseaseRef(BaseModel):
    """Disease identity in final backbone draft."""

    model_config = ConfigDict(extra="forbid")

    label: str
    ids: Dict[str, str | None] = Field(default_factory=dict)


class SourceSummary(BaseModel):
    """Summary statistics for source packets used."""

    model_config = ConfigDict(extra="forbid")

    source_packet_count: int = 0
    source_type_counts: Dict[str, int] = Field(default_factory=dict)


class BuildQuality(BaseModel):
    """Quality metrics of assembly output."""

    model_config = ConfigDict(extra="forbid")

    overall_confidence: float = 0.0
    items_needing_review: int = 0
    provisional_item_count: int = 0


class DiseaseBackboneDraft(BaseModel):
    """Top-level backbone draft artifact."""

    model_config = ConfigDict(extra="forbid")

    backbone_id: str
    builder_version: str
    disease: DraftDiseaseRef
    hallmarks: List[HallmarkCandidate] = Field(default_factory=list)
    modules: List[ModuleCandidate] = Field(default_factory=list)
    module_relations: List[ModuleRelation] = Field(default_factory=list)
    canonical_chains: List[CausalChainCandidate] = Field(default_factory=list)
    key_genes: List[KeyGeneCandidate] = Field(default_factory=list)
    source_summary: SourceSummary = Field(default_factory=SourceSummary)
    build_quality: BuildQuality = Field(default_factory=BuildQuality)
    status: Literal["draft"] = "draft"
