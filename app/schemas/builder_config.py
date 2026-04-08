"""Configuration schema for disease backbone building runs."""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

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


class BuilderDiseaseRef(BaseModel):
    """Disease identifiers used for one builder run."""

    model_config = ConfigDict(extra="forbid")

    label: str
    mondo_id: Optional[str] = None
    mesh_id: Optional[str] = None
    orphanet_id: Optional[str] = None


class SourcePolicy(BaseModel):
    """Source intake policy for packet generation."""

    model_config = ConfigDict(extra="forbid")

    preferred_source_types: List[SourceType] = Field(default_factory=list)
    max_packets_per_source: int = 20
    max_text_chars_per_packet: int = 12000


class LLMPolicy(BaseModel):
    """LLM extraction policy constraints."""

    model_config = ConfigDict(extra="forbid")

    provider: str = "mock"
    mode: Literal["json_constrained_extraction"] = "json_constrained_extraction"
    temperature: float = 0.1
    allow_world_knowledge: bool = False
    require_source_grounding: bool = True


class AggregationPolicy(BaseModel):
    """Policy values for aggregation/scoring/pruning."""

    model_config = ConfigDict(extra="forbid")

    min_support_for_core_module: int = 2
    min_support_for_core_hallmark: int = 2
    min_chain_confidence: float = 0.7
    generic_term_filter_enabled: bool = True


class OutputPolicy(BaseModel):
    """Policy for export formats and review outputs."""

    model_config = ConfigDict(extra="forbid")

    emit_review_flags: bool = True
    emit_provisional_items: bool = True
    formats: List[Literal["json", "jsonl", "csv"]] = Field(default_factory=lambda: ["json", "jsonl"])


class BuilderConfig(BaseModel):
    """Top-level config object for one disease backbone builder run."""

    model_config = ConfigDict(extra="forbid")

    builder_id: str = "disease_backbone_builder_v1"
    version: str = "1.0.0"
    disease: BuilderDiseaseRef
    source_policy: SourcePolicy = Field(default_factory=SourcePolicy)
    llm_policy: LLMPolicy = Field(default_factory=LLMPolicy)
    aggregation_policy: AggregationPolicy = Field(default_factory=AggregationPolicy)
    output_policy: OutputPolicy = Field(default_factory=OutputPolicy)
    source_weights: Dict[SourceType, float] = Field(
        default_factory=lambda: {
            "GeneReviews": 1.0,
            "Orphanet": 0.9,
            "ReviewArticle": 0.8,
            "ConsensusStatement": 0.8,
            "ReactomeSummary": 0.7,
            "GOSummary": 0.6,
            "ClinGenSummary": 0.8,
            "OMIMSummary": 0.7,
            "Other": 0.5,
        }
    )
