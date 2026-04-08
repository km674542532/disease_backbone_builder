"""Schema for run-level execution manifest."""
from __future__ import annotations

from typing import Dict, List

from pydantic import ConfigDict, Field

from app.schemas.artifact_record import ArtifactRecord
from app.schemas.base import SchemaModel
from app.schemas.enums import PipelineStage


class StageRecord(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    stage: PipelineStage
    status: str
    artifacts: List[ArtifactRecord] = Field(default_factory=list)


class RunManifest(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    disease: str
    builder_version: str
    stages: List[StageRecord] = Field(default_factory=list)
    output_paths: Dict[str, str] = Field(default_factory=dict)
