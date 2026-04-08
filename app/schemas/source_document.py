"""Schema for normalized source documents."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field

from app.schemas.base import SchemaModel
from app.schemas.enums import ReviewBucket, SourceType


class SourceLocator(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    pmid: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    internal_ref: Optional[str] = None


class SourceDocument(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    source_document_id: str
    disease_label: str
    source_type: SourceType
    source_name: str
    source_title: str
    source_locator: SourceLocator = Field(default_factory=SourceLocator)
    priority_tier: ReviewBucket
    selection_metadata: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
