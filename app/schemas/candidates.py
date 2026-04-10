"""Candidate schemas extracted from source packets."""
from __future__ import annotations

from typing import List, Literal

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import SchemaModel
from app.schemas.enums import CandidateStatus, GeneRole, MechanismCategory, ModuleType, RelationPredicate

EvidenceScope = Literal["disease_level", "module_level", "process_level"]


class SupportingSpan(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    source_packet_id: str
    quote: str


class HallmarkCandidate(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    label: str
    normalized_label: str
    description: str
    evidence_scope: EvidenceScope = "disease_level"
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    supporting_source_document_ids: List[str] = Field(default_factory=list)
    supporting_spans: List[SupportingSpan] = Field(default_factory=list)
    candidate_confidence: float
    status: CandidateStatus = "candidate"

    @model_validator(mode="after")
    def _validate_confidence(self) -> "HallmarkCandidate":
        if not (0.0 <= self.candidate_confidence <= 1.0):
            raise ValueError("confidence must be within 0-1")
        return self


class ModuleCandidate(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    label: str
    normalized_label: str
    description: str
    module_type: ModuleType
    mechanism_category: MechanismCategory = "proteostasis"
    hallmark_links: List[str] = Field(default_factory=list)
    key_genes: List[str] = Field(default_factory=list)
    process_terms: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    supporting_source_document_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float
    status: CandidateStatus = "candidate"

    @model_validator(mode="after")
    def _validate_confidence(self) -> "ModuleCandidate":
        if not (0.0 <= self.candidate_confidence <= 1.0):
            raise ValueError("confidence must be within 0-1")
        if self.evidence_count < 0:
            raise ValueError("evidence_count must be >= 0")
        return self


class ModuleRelation(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    subject_module: str
    predicate: RelationPredicate
    object_module: str
    description: str
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    supporting_source_document_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float

    @model_validator(mode="after")
    def _validate_confidence(self) -> "ModuleRelation":
        if not self.subject_module.strip() or not self.object_module.strip():
            raise ValueError("subject_module and object_module cannot be empty")
        if not (0.0 <= self.candidate_confidence <= 1.0):
            raise ValueError("confidence must be within 0-1")
        return self


class CausalStep(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    order: int
    event_label: str


class CausalChainCandidate(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    title: str
    module_label: str
    steps: List[CausalStep] = Field(default_factory=list)
    trigger_examples: List[str] = Field(default_factory=list)
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    supporting_source_document_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float
    status: CandidateStatus = "candidate"

    @model_validator(mode="after")
    def _validate_chain(self) -> "CausalChainCandidate":
        if self.steps and sorted(step.order for step in self.steps) != list(range(1, len(self.steps) + 1)):
            raise ValueError("causal chain step order must start at 1 and be contiguous")
        if self.steps and len(self.steps) < 3:
            raise ValueError("causal chain must have at least 3 steps")
        if not (0.0 <= self.candidate_confidence <= 1.0):
            raise ValueError("confidence must be within 0-1")
        return self


class KeyGeneCandidate(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    symbol: str
    gene_role: GeneRole
    linked_modules: List[str] = Field(default_factory=list)
    rationale: str
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    supporting_source_document_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float
    status: CandidateStatus = "candidate"

    @model_validator(mode="after")
    def _validate_confidence(self) -> "KeyGeneCandidate":
        if not self.symbol.strip():
            raise ValueError("gene symbol must not be empty")
        if not (0.0 <= self.candidate_confidence <= 1.0):
            raise ValueError("confidence must be within 0-1")
        return self
