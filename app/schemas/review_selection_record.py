"""Schema for ranked review triage decisions."""
from __future__ import annotations

from typing import List, Optional

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import SchemaModel
from app.schemas.enums import ReviewBucket, ReviewDecision


class ReviewSelectionRecord(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    selection_id: str
    pmid: str
    journal: str
    publication_year: int
    review_bucket: ReviewBucket
    impact_factor: Optional[float] = None
    impact_factor_source: Optional[str] = None
    review_rank_score: float
    mechanism_density_score: float
    disease_specificity_score: float
    decision: ReviewDecision
    reasons: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_review_scores(self) -> "ReviewSelectionRecord":
        for score in [self.review_rank_score, self.mechanism_density_score, self.disease_specificity_score]:
            if not (0.0 <= score <= 1.0):
                raise ValueError("review scores must be within 0-1")
        return self
