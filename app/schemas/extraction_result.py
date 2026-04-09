"""Schema for one source packet extraction result."""
from __future__ import annotations

from typing import List

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import SchemaModel
from app.schemas.candidates import (
    CausalChainCandidate,
    HallmarkCandidate,
    KeyGeneCandidate,
    ModuleCandidate,
    ModuleRelation,
)


class ExtractedDiseaseRef(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    mondo_id: str | None = None


class ExtractionQuality(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    llm_confidence: float
    needs_manual_review: bool = False
    warnings: List[str] = Field(default_factory=list)
    parse_status: str = "ok"
    schema_validation_status: str = "ok"

    @model_validator(mode="after")
    def _validate_llm_confidence(self) -> "ExtractionQuality":
        if not (0.0 <= self.llm_confidence <= 1.0):
            raise ValueError("llm_confidence must be within 0-1")
        return self


class ExtractionResult(SchemaModel):
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
