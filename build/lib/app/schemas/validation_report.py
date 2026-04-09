"""Validation report schema for assembled backbone drafts."""
from __future__ import annotations

from typing import Dict, List

from pydantic import ConfigDict, Field

from app.schemas.base import SchemaModel


class ValidationReport(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    backbone_id: str
    validation_passed: bool
    checks: Dict[str, bool] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    review_recommendations: List[str] = Field(default_factory=list)
