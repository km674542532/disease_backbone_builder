"""Prune and downgrade aggregated candidates using policy thresholds."""
from __future__ import annotations

from typing import Dict, List, Tuple

from app.schemas.builder_config import BuilderConfig

_GENERIC_TERMS = {"stress", "apoptosis", "inflammation", "metabolism", "signaling abnormality"}


class Pruner:
    """Assign core/provisional/dropped decisions by rule and keep audit prune log."""

    def prune(self, combined: Dict[str, list], config: BuilderConfig) -> Tuple[Dict[str, list], List[dict]]:
        prune_log: List[dict] = []

        kept_hallmarks = []
        for hallmark in combined.get("hallmarks", []):
            if len(hallmark.supporting_source_packet_ids) >= config.aggregation_policy.min_support_for_core_hallmark:
                hallmark.status = "candidate"
                action = "kept_core"
            else:
                hallmark.status = "provisional"
                action = "downgrade_low_support"
            prune_log.append({"type": "hallmark", "id": hallmark.candidate_id, "action": action})
            kept_hallmarks.append(hallmark)
        combined["hallmarks"] = kept_hallmarks

        kept_modules = []
        for module in combined.get("modules", []):
            status = "candidate"
            actions: List[str] = []
            normalized = module.normalized_label.lower()
            if config.aggregation_policy.generic_term_filter_enabled and any(term in normalized for term in _GENERIC_TERMS):
                status = "provisional"
                actions.append("downgrade_generic")
            if len(module.supporting_source_packet_ids) < config.aggregation_policy.min_support_for_core_module:
                status = "provisional"
                actions.append("downgrade_low_support")
            module.status = status
            prune_log.append({"type": "module", "id": module.candidate_id, "action": actions or ["kept_core"]})
            kept_modules.append(module)
        combined["modules"] = kept_modules

        kept_chains = []
        for chain in combined.get("chains", []):
            if len(chain.steps) < 3:
                chain.status = "provisional"
                prune_log.append({"type": "chain", "id": chain.candidate_id, "action": "drop_short_chain"})
                continue
            if chain.candidate_confidence < config.aggregation_policy.min_chain_confidence:
                chain.status = "provisional"
                prune_log.append({"type": "chain", "id": chain.candidate_id, "action": "downgrade_low_confidence"})
            else:
                chain.status = "candidate"
                prune_log.append({"type": "chain", "id": chain.candidate_id, "action": "kept_core"})
            kept_chains.append(chain)
        combined["chains"] = kept_chains

        for gene in combined.get("genes", []):
            if not gene.linked_modules:
                gene.status = "provisional"
                gene.gene_role = "uncertain"
                prune_log.append({"type": "gene", "id": gene.candidate_id, "action": "downgrade_no_module_link"})
            else:
                gene.status = "candidate"
                prune_log.append({"type": "gene", "id": gene.candidate_id, "action": "kept_core"})

        return combined, prune_log
