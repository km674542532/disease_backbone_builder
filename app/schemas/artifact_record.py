"""Schema for stage artifact metadata."""
from __future__ import annotations

from pydantic import ConfigDict

from app.schemas.base import SchemaModel
from app.schemas.enums import ArtifactStatus


class ArtifactRecord(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str
    path: str
    created_at: str
    count: int = 0
    status: ArtifactStatus
