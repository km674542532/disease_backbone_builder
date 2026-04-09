"""Schema for disease descriptor inputs (v1.1)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import ConfigDict, Field

from app.schemas.base import SchemaModel


class DiseaseIds(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    mondo: Optional[str] = None
    mesh: Optional[str] = None
    orphanet: Optional[str] = None
    omim: Optional[str] = None


class ScopePolicy(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    prefer_disease_central_mechanisms: bool = True
    allow_supporting_modules: bool = True
    allow_peripheral_modules: bool = True
    full_graph_expansion_in_scope: bool = False


class DiseaseDescriptor(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    synonyms: List[str] = Field(default_factory=list)
    ids: DiseaseIds = Field(default_factory=DiseaseIds)
    seed_genes: List[str] = Field(default_factory=list)
    disease_scope_note: str = "Build a disease-level mechanistic backbone, not full phenome coverage."
    scope_policy: ScopePolicy = Field(default_factory=ScopePolicy)
