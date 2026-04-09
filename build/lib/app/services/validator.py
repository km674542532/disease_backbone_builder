"""Validate assembled backbone draft against MVP checks."""
from __future__ import annotations

from app.schemas.backbone_draft import DiseaseBackboneDraft
from app.schemas.builder_config import BuilderConfig
from app.schemas.validation_report import ValidationReport

_GENERIC_TERMS = ["stress", "apoptosis", "inflammation", "metabolism", "signaling abnormality"]


class Validator:
    """Run framework-aligned validation checks and emit ValidationReport."""

    def validate(self, draft: DiseaseBackboneDraft, config: BuilderConfig | None = None) -> ValidationReport:
        min_hallmark_support = config.aggregation_policy.min_support_for_core_hallmark if config else 2
        min_module_support = config.aggregation_policy.min_support_for_core_module if config else 2

        core_hallmarks = [h for h in draft.hallmarks if h.status == "candidate"]
        core_modules = [m for m in draft.modules if m.status == "candidate"]

        checks = {
            "hallmark_count_ok": len(draft.hallmarks) >= 1,
            "module_count_ok": len(draft.modules) >= 1,
            "all_core_hallmarks_min_support": all(
                len(h.supporting_source_packet_ids) >= min_hallmark_support for h in core_hallmarks
            ),
            "all_core_modules_min_support": all(
                len(m.supporting_source_packet_ids) >= min_module_support for m in core_modules
            ),
            "all_core_items_have_source": all(
                len(item.supporting_source_packet_ids) >= 1
                for item in [*core_hallmarks, *core_modules, *draft.canonical_chains, *draft.key_genes]
            ),
            "all_chains_have_multiple_steps": all(len(c.steps) >= 3 for c in draft.canonical_chains),
            "generic_module_filter_passed": all(
                not any(term in m.normalized_label.lower() for term in _GENERIC_TERMS) or m.status == "provisional"
                for m in draft.modules
            ),
            "all_key_genes_linked_to_module": all(len(g.linked_modules) >= 1 for g in draft.key_genes),
        }

        warnings = []
        if not checks["all_core_hallmarks_min_support"]:
            warnings.append("One or more candidate hallmarks do not meet minimum support.")
        if not checks["all_core_modules_min_support"]:
            warnings.append("One or more candidate modules do not meet minimum support.")
        if not checks["all_chains_have_multiple_steps"]:
            warnings.append("One or more canonical chains have fewer than 3 steps.")

        return ValidationReport(
            backbone_id=draft.backbone_id,
            validation_passed=all(checks.values()),
            checks=checks,
            warnings=warnings,
            review_recommendations=["Review provisional items and ensure source grounding coverage."],
        )
