"""Schema for disease descriptor inputs."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class DiseaseIds(BaseModel):
    """External disease IDs."""

    model_config = ConfigDict(extra="forbid")

    mondo: Optional[str] = None
    mesh: Optional[str] = None
    orphanet: Optional[str] = None
    omim: Optional[str] = None


class DiseaseDescriptor(BaseModel):
    """Disease definition for one builder run."""

    model_config = ConfigDict(extra="forbid")

    label: str
    synonyms: List[str] = Field(default_factory=list)
    ids: DiseaseIds = Field(default_factory=DiseaseIds)
    seed_genes: List[str] = Field(default_factory=list)
    disease_scope_note: str = (
        "Build a mechanistic backbone for disease-level causal interpretation, not full phenome coverage."
    )
