"""Final disease backbone draft schema."""
from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import SchemaModel
from app.schemas.candidates import (
    CausalChainCandidate,
    HallmarkCandidate,
    KeyGeneCandidate,
    ModuleCandidate,
    ModuleRelation,
)


class DraftDiseaseRef(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    ids: Dict[str, str | None] = Field(default_factory=dict)


class SourceSummary(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    source_document_count: int = 0
    source_packet_count: int = 0
    source_type_counts: Dict[str, int] = Field(default_factory=dict)


class LiteratureSummary(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    pubmed_candidate_count: int = 0
    selected_review_count: int = 0
    selected_systematic_review_count: int = 0
    selected_specialized_review_count: int = 0


class BuildQuality(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    overall_confidence: float = 0.0
    items_needing_review: int = 0
    provisional_item_count: int = 0
    schema_pass_rate: float = 0.0
    filtered_item_count: int = 0
    review_queue_count: int = 0
    grounded_core_module_count: int = 0

    @model_validator(mode="after")
    def _validate_overall_confidence(self) -> "BuildQuality":
        if not (0.0 <= self.overall_confidence <= 1.0):
            raise ValueError("overall_confidence must be within 0-1")
        if not (0.0 <= self.schema_pass_rate <= 1.0):
            raise ValueError("schema_pass_rate must be within 0-1")
        return self


class DiseaseBackboneDraft(SchemaModel):
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
    literature_summary: LiteratureSummary = Field(default_factory=LiteratureSummary)
    build_quality: BuildQuality = Field(default_factory=BuildQuality)
    status: Literal["draft", "candidate", "provisional"] = "draft"
