"""Schema for one source packet extraction result."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.candidates import (
    CausalChainCandidate,
    HallmarkCandidate,
    KeyGeneCandidate,
    ModuleCandidate,
    ModuleRelation,
)


class ExtractedDiseaseRef(BaseModel):
    """Disease identity included in extraction result."""

    model_config = ConfigDict(extra="forbid")

    label: str
    mondo_id: str | None = None


class ExtractionQuality(BaseModel):
    """Extraction quality and review flags."""

    model_config = ConfigDict(extra="forbid")

    llm_confidence: float
    needs_manual_review: bool = False
    warnings: List[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Structured extraction output produced per source packet."""

    model_config = ConfigDict(extra="forbid")

    source_packet_id: str
    disease: ExtractedDiseaseRef
    hallmarks: List[HallmarkCandidate] = Field(default_factory=list)
    modules: List[ModuleCandidate] = Field(default_factory=list)
    module_relations: List[ModuleRelation] = Field(default_factory=list)
    causal_chains: List[CausalChainCandidate] = Field(default_factory=list)
    key_genes: List[KeyGeneCandidate] = Field(default_factory=list)
    global_notes: List[str] = Field(default_factory=list)
    extraction_quality: ExtractionQuality
