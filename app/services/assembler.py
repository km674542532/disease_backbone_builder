"""Assemble final DiseaseBackboneDraft artifact."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from app.schemas.backbone_draft import BuildQuality, DiseaseBackboneDraft, DraftDiseaseRef, SourceSummary
from app.schemas.builder_config import BuilderConfig
from app.schemas.disease_descriptor import DiseaseDescriptor


class Assembler:
    """Build final draft object from pruned combined candidates."""

    def assemble(
        self,
        disease: DiseaseDescriptor,
        config: BuilderConfig,
        combined: Dict[str, list],
        source_types_by_packet: Dict[str, str],
    ) -> DiseaseBackboneDraft:
        type_counts = Counter(source_types_by_packet.values())
        all_conf = [x.candidate_confidence for key in ("hallmarks", "modules", "chains", "genes") for x in combined.get(key, [])]
        provisional_count = sum(1 for key in ("hallmarks", "modules", "chains") for x in combined.get(key, []) if getattr(x, "status", "candidate") == "provisional")
        return DiseaseBackboneDraft(
            backbone_id=f"{disease.label.lower().replace(' ', '_')}_backbone_draft_v1",
            builder_version=config.version,
            disease=DraftDiseaseRef(label=disease.label, ids=disease.ids.model_dump()),
            hallmarks=combined.get("hallmarks", []),
            modules=combined.get("modules", []),
            module_relations=[],
            canonical_chains=combined.get("chains", []),
            key_genes=combined.get("genes", []),
            source_summary=SourceSummary(source_packet_count=len(source_types_by_packet), source_type_counts=dict(type_counts)),
            build_quality=BuildQuality(
                overall_confidence=round(sum(all_conf) / max(1, len(all_conf)), 4),
                items_needing_review=provisional_count,
                provisional_item_count=provisional_count,
            ),
            status="draft",
        )
