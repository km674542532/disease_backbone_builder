"""Candidate schemas extracted from source packets."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, ConfigDict

EvidenceScope = Literal["disease_level", "module_level", "process_level"]
CandidateStatus = Literal["candidate", "provisional", "core", "filtered"]
ModuleType = Literal[
    "core_mechanism_module",
    "supporting_module",
    "phenotype_convergence_module",
    "peripheral_module",
]
RelationPredicate = Literal[
    "upstream_of",
    "downstream_of",
    "interacts_with",
    "converges_on",
    "amplifies",
    "impairs",
    "supports",
    "linked_to",
]
GeneRole = Literal[
    "core_driver",
    "major_associated_gene",
    "module_specific_gene",
    "supporting_gene",
    "uncertain",
]


class SupportingSpan(BaseModel):
    """One support quote for a candidate."""

    model_config = ConfigDict(extra="forbid")

    source_packet_id: str
    quote: str


class HallmarkCandidate(BaseModel):
    """Hallmark-level mechanism candidate."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    label: str
    normalized_label: str
    description: str
    evidence_scope: EvidenceScope = "disease_level"
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    supporting_spans: List[SupportingSpan] = Field(default_factory=list)
    candidate_confidence: float
    status: CandidateStatus = "candidate"


class ModuleCandidate(BaseModel):
    """Module-level candidate."""

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
    candidate_confidence: float
    status: CandidateStatus = "candidate"


class ModuleRelation(BaseModel):
    """Relation candidate between two modules."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    subject_module: str
    predicate: RelationPredicate
    object_module: str
    description: str
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float


class CausalStep(BaseModel):
    """One ordered step in a causal chain."""

    model_config = ConfigDict(extra="forbid")

    order: int
    event_label: str


class CausalChainCandidate(BaseModel):
    """Candidate disease-relevant causal chain."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    title: str
    module_label: str
    steps: List[CausalStep] = Field(default_factory=list)
    trigger_examples: List[str] = Field(default_factory=list)
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float
    status: CandidateStatus = "candidate"


class KeyGeneCandidate(BaseModel):
    """Key gene candidate with module links."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    symbol: str
    gene_role: GeneRole
    linked_modules: List[str] = Field(default_factory=list)
    rationale: str
    supporting_source_packet_ids: List[str] = Field(default_factory=list)
    candidate_confidence: float
