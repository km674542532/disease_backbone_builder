"""Controlled vocabulary literal type aliases used across schemas."""
from __future__ import annotations

from typing import Literal

SourceType = Literal[
    "GeneReviews",
    "Orphanet",
    "ReviewArticle",
    "SystematicReview",
    "SpecializedReview",
    "ConsensusStatement",
    "ReactomeSummary",
    "GOSummary",
    "ClinGenSummary",
    "OMIMSummary",
    "Other",
]

ReviewBucket = Literal[
    "authoritative",
    "anchor_review",
    "systematic_review",
    "specialized_review",
    "supplementary_review",
    "rejected",
]

CandidateStatus = Literal["candidate", "provisional", "core-draft", "filtered", "review"]
ModuleType = Literal[
    "core_mechanism_module",
    "supporting_module",
    "phenotype_module",
    "peripheral_module",
]
MechanismCategory = Literal[
    "proteostasis",
    "alpha_synuclein",
    "mitochondrial",
    "lysosome_autophagy",
    "neuroinflammation",
    "synaptic",
    "vesicle_trafficking",
    "oxidative_stress",
    "metal_homeostasis",
    "gut_brain_axis",
    "phenotype",
    "intervention",
    "biomarker",
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
    "driver",
    "modifier",
    "biomarker",
    "uncertain",
]
ModuleRecordType = Literal["hallmark", "module", "chain", "gene", "relation"]
ReviewDecision = Literal["selected", "rejected", "holdout"]
ArtifactStatus = Literal["started", "completed", "failed"]
PipelineStage = Literal[
    "disease_initialization",
    "authoritative_source_collection",
    "pubmed_review_discovery",
    "review_retrieval",
    "review_normalization_dedup",
    "review_ranking_triage",
    "source_manifest_freeze",
    "source_packetization",
    "extraction",
    "normalization",
    "aggregation",
    "scoring_pruning",
    "assembly",
    "validation",
    "review_package_export",
]
