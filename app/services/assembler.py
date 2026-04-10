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
        *,
        review_queue_count: int = 0,
        filtered_item_count: int = 0,
        schema_pass_rate: float = 1.0,
    ) -> DiseaseBackboneDraft:
        type_counts = Counter(source_types_by_packet.values())
        all_items = [item for key in ("hallmarks", "modules", "chains", "genes") for item in combined.get(key, [])]
        all_conf = [item.candidate_confidence for item in all_items] or [0.0]
        provisional_count = sum(1 for item in all_items if getattr(item, "status", "candidate") == "provisional")
        grounded_core_modules = sum(
            1
            for m in combined.get("modules", [])
            if m.status == "candidate" and m.module_type == "core_mechanism_module" and m.key_genes and m.process_terms and m.description.strip()
        )

        return DiseaseBackboneDraft(
            backbone_id="pd_backbone_draft_v2",
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
                items_needing_review=provisional_count + review_queue_count,
                provisional_item_count=provisional_count,
                schema_pass_rate=round(schema_pass_rate, 4),
                filtered_item_count=filtered_item_count,
                review_queue_count=review_queue_count,
                grounded_core_module_count=grounded_core_modules,
            ),
            status="draft",
        )
