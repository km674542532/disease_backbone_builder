from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable

from app.schemas.source_document import SourceDocument
from app.schemas.source_packet import SourcePacket

TIER_WEIGHTS = {
    "tier_1_curated_disease_reference": 1.0,
    "tier_2_systematic_review": 0.9,
    "tier_2_high_quality_review": 0.8,
    "tier_3_specialized_review": 0.65,
    "tier_4_other_review": 0.45,
    "tier_5_unknown": 0.2,
}


def infer_source_tier(source_type: str, title: str, metadata: Dict[str, object] | None = None) -> str:
    lowered = (title or "").lower()
    source_type = (source_type or "").lower()
    metadata = metadata or {}
    if source_type in {"genereviews", "orphanet", "omimsummary", "clingensummary"}:
        return "tier_1_curated_disease_reference"
    if "systematic review" in lowered or metadata.get("is_systematic_review"):
        return "tier_2_systematic_review"
    if "overview" in lowered or "consensus" in lowered:
        return "tier_2_high_quality_review"
    if source_type in {"specializedreview", "reactomesummary", "gosummary"}:
        return "tier_3_specialized_review"
    if "review" in lowered:
        return "tier_4_other_review"
    return "tier_5_unknown"


def compute_source_weight(source_tier: str, selection_metadata: Dict[str, object] | None = None) -> float:
    weight = TIER_WEIGHTS.get(source_tier, 0.2)
    selection_metadata = selection_metadata or {}
    if selection_metadata.get("is_authoritative"):
        weight += 0.1
    if selection_metadata.get("disease_specificity", 0) and float(selection_metadata.get("disease_specificity", 0)) > 0.8:
        weight += 0.05
    return round(min(1.0, weight), 4)


def apply_source_quality(source_docs: Iterable[Any], packets: Iterable[SourcePacket]) -> Dict[str, Dict[str, float | str]]:
    by_packet: Dict[str, Dict[str, float | str]] = {}
    by_doc: Dict[str, Dict[str, float | str]] = {}
    for doc in source_docs:
        if isinstance(doc, SourceDocument):
            source_type = doc.source_type
            title = doc.source_title
            metadata = doc.metadata
            sel = doc.selection_metadata
            doc_id = doc.source_document_id
        else:
            source_type = str(doc.get("source_type", "Other"))
            title = str(doc.get("source_title", ""))
            metadata = doc.get("metadata", {}) or {}
            sel = doc.get("selection_metadata", {}) or {}
            doc_id = str(doc.get("source_document_id", doc.get("id", title)))
        tier = infer_source_tier(source_type, title, metadata)
        weight = compute_source_weight(tier, sel)
        by_doc[doc_id] = {"source_tier": tier, "source_weight": weight}
    for packet in packets:
        tier = infer_source_tier(packet.source_type, packet.source_title, packet.metadata)
        weight = compute_source_weight(tier, packet.selection_metadata)
        packet.source_tier = tier
        packet.source_weight = weight
        by_packet[packet.source_packet_id] = {"source_tier": tier, "source_weight": weight}
    return by_packet


def source_tier_distribution(packets: Iterable[SourcePacket]) -> Dict[str, int]:
    return dict(Counter(packet.source_tier for packet in packets))
