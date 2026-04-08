"""Validation report schema for assembled backbone drafts."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field, ConfigDict


class ValidationReport(BaseModel):
    """Output for post-assembly quality checks."""

    model_config = ConfigDict(extra="forbid")

    backbone_id: str
    validation_passed: bool
    checks: Dict[str, bool] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    review_recommendations: List[str] = Field(default_factory=list)
