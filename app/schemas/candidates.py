"""Candidate schemas extracted from source packets."""
from __future__ import annotations

from typing import List, Literal

from pydantic import ConfigDict, Field

from app.schemas.base import SchemaModel
from app.schemas.enums import CandidateStatus, GeneRole, ModuleType, RelationPredicate

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


class ModuleCandidate(SchemaModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    label: str
    normalized_label: str
    description: str
    module_type: ModuleType
    hallmark_links: List[str] = Field(default_factory=list)
    key_genes: List[str] = Field(default_factory=list)
    process_terms: List[str] = Field(default_factory=list)
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    supporting_source_document_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float
    status: CandidateStatus = "candidate"


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

    def __init__(self, **data):
        super().__init__(**data)
        if self.steps and sorted(step.order for step in self.steps) != list(range(1, len(self.steps) + 1)):
            from pydantic import ValidationError
            raise ValidationError("causal chain step order must start at 1 and be contiguous")


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


def _check_confidence(v: float) -> None:
    if not (0.0 <= v <= 1.0):
        from pydantic import ValidationError
        raise ValidationError("confidence must be within 0-1")


for _klass in [HallmarkCandidate, ModuleCandidate, ModuleRelation, CausalChainCandidate, KeyGeneCandidate]:
    _orig_init = _klass.__init__

    def _wrapped_init(self, __orig_init=_orig_init, **data):
        __orig_init(self, **data)
        _check_confidence(self.candidate_confidence)

    _klass.__init__ = _wrapped_init
