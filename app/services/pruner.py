"""Prune and downgrade aggregated candidates using policy thresholds."""
from __future__ import annotations

from typing import Dict, List, Tuple

from app.schemas.builder_config import BuilderConfig

_GENERIC_TERMS = {"stress", "apoptosis", "inflammation", "metabolism", "signaling abnormality"}


class Pruner:
    """Applies MVP pruning policy to aggregated items."""

    def prune(self, combined: Dict[str, list], config: BuilderConfig) -> Tuple[Dict[str, list], List[dict]]:
        prune_log: List[dict] = []

        kept_modules = []
        for module in combined["modules"]:
            norm = module.normalized_label
            if any(t in norm for t in _GENERIC_TERMS):
                module.status = "provisional"
                prune_log.append({"type": "module", "id": module.candidate_id, "action": "downgrade_generic"})
            if len(module.supporting_source_packet_ids) < config.aggregation_policy.min_support_for_core_module:
                module.status = "provisional"
                prune_log.append({"type": "module", "id": module.candidate_id, "action": "downgrade_low_support"})
            kept_modules.append(module)
        combined["modules"] = kept_modules

        combined["chains"] = [
            c for c in combined["chains"] if len(c.steps) >= 3 or not prune_log.append({"type": "chain", "id": c.candidate_id, "action": "drop_short_chain"})
        ]

        for gene in combined["genes"]:
            if not gene.linked_modules:
                gene.gene_role = "uncertain"
                prune_log.append({"type": "gene", "id": gene.candidate_id, "action": "downgrade_no_module_link"})

        return combined, prune_log
