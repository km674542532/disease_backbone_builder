"""Structured rule configuration for backbone v1.1."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from pydantic import ConfigDict, Field, ValidationError, model_validator

from app.schemas.base import SchemaModel


class HallmarkRules(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    min_support_for_core_hallmark: int = 2
    generic_filter_terms: List[str] = Field(default_factory=list)


class ModuleRules(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    min_support_for_core_module: int = 2
    allowed_module_types: List[str] = Field(default_factory=lambda: ["core_mechanism_module", "supporting_module"])
    generic_filter_terms: List[str] = Field(default_factory=list)


class ChainRules(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    min_steps: int = 3
    min_chain_confidence: float = 0.7


class GeneRules(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    allowed_gene_roles: List[str] = Field(default_factory=list)
    require_module_link: bool = True


class ReviewSelectionRules(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    min_publication_year: int = 2018
    allowed_languages: List[str] = Field(default_factory=lambda: ["eng"])
    max_selected_reviews: int = 10
    max_selected_systematic_reviews: int = 5
    max_selected_specialized_reviews: int = 8


class ReviewRankingWeights(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    review_type_weight: float = 0.3
    recency_weight: float = 0.2
    impact_factor_weight: float = 0.2
    mechanism_density_weight: float = 0.2
    disease_specificity_weight: float = 0.1


class RuleConfig(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    hallmark_rules: HallmarkRules = Field(default_factory=HallmarkRules)
    module_rules: ModuleRules = Field(default_factory=ModuleRules)
    chain_rules: ChainRules = Field(default_factory=ChainRules)
    gene_rules: GeneRules = Field(default_factory=GeneRules)
    source_weights: Dict[str, float] = Field(default_factory=dict)
    review_selection_rules: ReviewSelectionRules = Field(default_factory=ReviewSelectionRules)
    review_ranking_weights: ReviewRankingWeights = Field(default_factory=ReviewRankingWeights)

    @model_validator(mode="after")
    def _validate_weights(self) -> "RuleConfig":
        for weight in [
            self.chain_rules.min_chain_confidence,
            self.review_ranking_weights.review_type_weight,
            self.review_ranking_weights.recency_weight,
            self.review_ranking_weights.impact_factor_weight,
            self.review_ranking_weights.mechanism_density_weight,
            self.review_ranking_weights.disease_specificity_weight,
        ]:
            if not (0.0 <= weight <= 1.0):
                raise ValueError("rule confidence/weights must be within 0-1")
        return self


def load_rule_config(path: str | Path) -> RuleConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Rule config file not found: {config_path}")

    suffix = config_path.suffix.lower()
    raw_text = config_path.read_text(encoding="utf-8")
    try:
        if suffix in {".yaml", ".yml"}:
            import yaml  # type: ignore

            payload = yaml.safe_load(raw_text)
        elif suffix == ".json":
            payload = json.loads(raw_text)
        else:
            raise ValueError(f"Unsupported rule config format: {suffix}")
    except Exception as exc:
        raise ValueError(f"Failed to parse rule config {config_path}: {exc}") from exc

    try:
        return RuleConfig.from_dict(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid rule config schema in {config_path}: {exc}") from exc
