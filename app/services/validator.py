"""Validate assembled backbone draft against production checks."""
from __future__ import annotations

from app.schemas.backbone_draft import DiseaseBackboneDraft
from app.schemas.builder_config import BuilderConfig
from app.schemas.validation_report import ValidationReport


class Validator:
    """Run validation checks and emit ValidationReport."""

    def validate(self, draft: DiseaseBackboneDraft, config: BuilderConfig | None = None) -> ValidationReport:
        min_hallmark_support = config.aggregation_policy.min_support_for_core_hallmark if config else 2
        min_module_support = config.aggregation_policy.min_support_for_core_module if config else 2

        core_hallmarks = [h for h in draft.hallmarks if h.status == "candidate"]
        core_modules = [m for m in draft.modules if m.status == "candidate" and m.module_type == "core_mechanism_module"]

        checks = {
            "hallmark_count_ok": len(draft.hallmarks) >= 1,
            "module_count_ok": len(draft.modules) >= 1,
            "all_core_hallmarks_min_support": all(len(h.supporting_source_packet_ids) >= min_hallmark_support for h in core_hallmarks),
            "all_core_modules_min_support": all(len(m.supporting_source_packet_ids) >= min_module_support for m in core_modules),
            "all_core_items_have_source": all(
                len(item.supporting_source_packet_ids) >= 1 for item in [*core_hallmarks, *core_modules, *draft.canonical_chains, *draft.key_genes]
            ),
            "all_chains_have_multiple_steps": all(len(c.steps) >= 3 for c in draft.canonical_chains),
            "all_key_genes_linked_to_module": all(len(g.linked_modules) >= 1 for g in draft.key_genes),
            "no_unknown_hallmark": all(h.normalized_label != "unknown_hallmark" for h in draft.hallmarks),
            "no_empty_relation_nodes": all(r.subject_module.strip() and r.object_module.strip() for r in draft.module_relations),
            "all_key_genes_have_symbol": all(g.symbol.strip() for g in draft.key_genes),
            "all_core_modules_have_minimum_content": all(m.description.strip() and m.key_genes and m.process_terms for m in core_modules),
            "phenotype_not_mixed_into_core": all(m.module_type != "core_mechanism_module" for m in draft.modules if m.mechanism_category == "phenotype"),
            "at_least_one_canonical_chain": len(draft.canonical_chains) >= 1,
            "core_module_confidence_nonzero": all(m.candidate_confidence > 0 for m in core_modules),
            "no_zero_confidence_for_core_items": all(
                x.candidate_confidence > 0 for x in [*core_hallmarks, *core_modules] if getattr(x, "status", "") in {"core-draft", "candidate"}
            ),
            "all_core_items_meet_weighted_support_threshold": all(
                getattr(x, "source_weighted_support", getattr(x, "weighted_support_score", 0.0)) >= 0.45
                for x in [*core_hallmarks, *core_modules]
                if getattr(x, "status", "") in {"core-draft", "candidate"}
            ),
            "all_symbols_normalized_or_flagged": all(g.normalized_symbol or g.status in {"review", "provisional"} for g in draft.key_genes),
            "no_duplicate_normalized_modules": len({m.normalized_label for m in draft.modules}) == len(draft.modules),
            "graph_has_connected_core_component": len(draft.canonical_chains) > 0 and any(len(c.steps) >= 3 for c in draft.canonical_chains),
            "at_least_three_ranked_canonical_chains": len(draft.canonical_chains) >= 3,
            "phenotype_layer_separated_from_core_mechanism_layer": all(
                m.module_type != "core_mechanism_module" for m in draft.modules if m.mechanism_category == "phenotype"
            ),
        }

        warnings = [name for name, passed in checks.items() if not passed]
        return ValidationReport(
            backbone_id=draft.backbone_id,
            validation_passed=all(checks.values()),
            checks=checks,
            warnings=warnings,
            review_recommendations=["Review queue items and provisional modules before mechanism modeling."],
        )
