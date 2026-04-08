"""Validate assembled backbone draft against MVP checks."""
from __future__ import annotations

from app.schemas.backbone_draft import DiseaseBackboneDraft
from app.schemas.validation_report import ValidationReport


class Validator:
    """Run core quality checks and emit validation report."""

    def validate(self, draft: DiseaseBackboneDraft) -> ValidationReport:
        checks = {
            "hallmark_count_ok": 1 <= len(draft.hallmarks) <= 8,
            "module_count_ok": 1 <= len(draft.modules) <= 12,
            "all_core_modules_have_support": all(len(m.supporting_source_packet_ids) >= 1 for m in draft.modules if m.status in {"candidate", "core"}),
            "all_chains_have_multiple_steps": all(len(c.steps) >= 3 for c in draft.canonical_chains),
            "all_key_genes_linked_to_module": all(len(g.linked_modules) >= 1 for g in draft.key_genes),
            "generic_module_filter_passed": all(
                not any(term in m.normalized_label for term in ["stress", "apoptosis", "inflammation", "metabolism", "signaling abnormality"])
                or m.status == "provisional"
                for m in draft.modules
            ),
        }
        warnings = []
        if not checks["module_count_ok"]:
            warnings.append("Module count out of expected MVP range [1, 12].")
        if not checks["all_chains_have_multiple_steps"]:
            warnings.append("One or more chains have fewer than 3 steps.")
        return ValidationReport(
            backbone_id=draft.backbone_id,
            validation_passed=all(checks.values()),
            checks=checks,
            warnings=warnings,
            review_recommendations=["Review provisional modules and uncertain genes."],
        )
