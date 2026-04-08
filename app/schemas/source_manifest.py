"""Schema for frozen source manifest used in one run."""
from __future__ import annotations

from typing import List

from pydantic import ConfigDict, Field

from app.schemas.base import SchemaModel


class SourceManifest(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    disease_label: str
    authoritative_source_document_ids: List[str] = Field(default_factory=list)
    selected_review_source_document_ids: List[str] = Field(default_factory=list)
