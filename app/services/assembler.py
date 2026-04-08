"""Assemble final DiseaseBackboneDraft artifact."""
from __future__ import annotations

from collections import Counter
from typing import Dict

from app.schemas.backbone_draft import BuildQuality, DiseaseBackboneDraft, DraftDiseaseRef, SourceSummary
from app.schemas.builder_config import BuilderConfig
from app.schemas.disease_descriptor import DiseaseDescriptor


class Assembler:
    """Build the disease-level backbone draft from pruned candidates."""

    def assemble(
        self,
        disease: DiseaseDescriptor,
        config: BuilderConfig,
        combined: Dict[str, list],
        source_types_by_packet: Dict[str, str],
    ) -> DiseaseBackboneDraft:
        type_counts = Counter(source_types_by_packet.values())
        all_items = [
            item
            for key in ("hallmarks", "modules", "chains", "genes")
            for item in combined.get(key, [])
        ]
        all_conf = [item.candidate_confidence for item in all_items] or [0.0]
        provisional_count = sum(1 for item in all_items if getattr(item, "status", "candidate") == "provisional")

        return DiseaseBackboneDraft(
            backbone_id="pd_backbone_draft_v1_1",
            builder_version=config.version,
            disease=DraftDiseaseRef(label=disease.label, ids=disease.ids.model_dump()),
            hallmarks=combined.get("hallmarks", []),
            modules=combined.get("modules", []),
            module_relations=combined.get("relations", []),
            canonical_chains=combined.get("chains", []),
            key_genes=combined.get("genes", []),
            source_summary=SourceSummary(
                source_packet_count=len(source_types_by_packet),
                source_type_counts=dict(type_counts),
            ),
            build_quality=BuildQuality(
                overall_confidence=round(sum(all_conf) / len(all_conf), 4),
                items_needing_review=provisional_count,
                provisional_item_count=provisional_count,
            ),
            status="draft",
        )
