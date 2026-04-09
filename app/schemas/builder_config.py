"""Configuration schema for disease backbone building runs (v1.1)."""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import SchemaModel
from app.schemas.enums import SourceType


class BuilderDiseaseRef(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    mondo_id: Optional[str] = None
    mesh_id: Optional[str] = None
    orphanet_id: Optional[str] = None


class SourcePolicy(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    preferred_source_types: List[SourceType] = Field(default_factory=list)
    max_documents_per_source_type: int = 20
    max_packets_per_source: int = 30
    max_text_chars_per_packet: int = 12000


class LiteraturePolicy(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    enable_pubmed_review_discovery: bool = True
    max_pubmed_candidates: int = 200
    min_publication_year: int = 2018
    languages: List[str] = Field(default_factory=lambda: ["eng"])
    publication_types: List[str] = Field(default_factory=lambda: ["Review"])
    allow_systematic_review_subset: bool = True
    max_selected_reviews: int = 10
    max_selected_systematic_reviews: int = 5
    max_selected_specialized_reviews: int = 8


class LLMPolicy(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "qwen"
    mode: Literal["json_constrained_extraction"] = "json_constrained_extraction"
    temperature: float = 0.1
    allow_world_knowledge: bool = False
    require_source_grounding: bool = True
    emit_raw_response: bool = True


class AggregationPolicy(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    min_support_for_core_module: int = 2
    min_support_for_core_hallmark: int = 2
    min_chain_confidence: float = 0.7
    generic_term_filter_enabled: bool = True


class RankingPolicy(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    use_impact_factor: bool = True
    impact_factor_weight: float = 0.2
    recency_weight: float = 0.2
    review_type_weight: float = 0.3
    mechanism_density_weight: float = 0.2
    disease_specificity_weight: float = 0.1


class OutputPolicy(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    emit_review_flags: bool = True
    emit_provisional_items: bool = True
    formats: List[Literal["json", "jsonl", "csv"]] = Field(default_factory=lambda: ["json", "jsonl"])


class BuilderConfig(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    builder_id: str = "disease_backbone_builder_v1_1"
    version: str = "1.1.0"
    disease: BuilderDiseaseRef
    source_policy: SourcePolicy = Field(default_factory=SourcePolicy)
    literature_policy: LiteraturePolicy = Field(default_factory=LiteraturePolicy)
    llm_policy: LLMPolicy = Field(default_factory=LLMPolicy)
    aggregation_policy: AggregationPolicy = Field(default_factory=AggregationPolicy)
    ranking_policy: RankingPolicy = Field(default_factory=RankingPolicy)
    output_policy: OutputPolicy = Field(default_factory=OutputPolicy)
    source_weights: Dict[SourceType, float] = Field(
        default_factory=lambda: {
            "GeneReviews": 1.0,
            "Orphanet": 0.95,
            "ClinGenSummary": 0.9,
            "OMIMSummary": 0.9,
            "ReviewArticle": 0.8,
            "SystematicReview": 0.85,
            "SpecializedReview": 0.75,
            "Other": 0.5,
        }
    )

    @model_validator(mode="after")
    def _validate_weights(self) -> "BuilderConfig":
        for field in [
            self.aggregation_policy.min_chain_confidence,
            self.ranking_policy.impact_factor_weight,
            self.ranking_policy.recency_weight,
            self.ranking_policy.review_type_weight,
            self.ranking_policy.mechanism_density_weight,
            self.ranking_policy.disease_specificity_weight,
        ]:
            if not (0.0 <= field <= 1.0):
                raise ValueError("config confidence/weight fields must be within 0-1")
        return self
