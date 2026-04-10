"""Production-oriented backbone v2 refinement layer."""
from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml

from app.schemas.candidates import CausalChainCandidate, CausalStep, HallmarkCandidate, KeyGeneCandidate, ModuleCandidate
from app.utils.ontology_mapper import merge_synonym_label
from app.utils.text_normalize import normalize_label

logger = logging.getLogger(__name__)

_NOISE_TERMS = {
    "dance",
    "walking",
    "tdcs",
    "quality of life",
    "clinical management",
    "management",
}
_PHENOTYPE_TERMS = {"motor symptoms", "mood disorders", "urogenital dysfunction", "non-motor phenotype", "motor phenotype"}
_INTERVENTION_TERMS = {"stimulation", "drug", "therapy", "intervention", "rehabilitation"}
_SEED_TO_CATEGORY = {
    "alpha-synuclein aggregation": "alpha_synuclein",
    "dopaminergic neuron degeneration": "phenotype",
    "mitochondrial dysfunction": "mitochondrial",
    "lysosomal/autophagy dysfunction": "lysosome_autophagy",
    "neuroinflammation": "neuroinflammation",
}
_CORE_PD_GENES = {"SNCA", "LRRK2", "GBA", "PRKN", "PINK1", "VPS35", "PARK7", "ATP13A2"}


class BackboneV2Refiner:
    def __init__(self, seed_path: str = "data/seeds/pd_hallmark_seeds.yaml") -> None:
        self.seed_path = seed_path
        self.hallmark_seeds = self._load_hallmark_seeds(seed_path)

    def _load_hallmark_seeds(self, path: str) -> Set[str]:
        fp = Path(path)
        if not fp.exists():
            logger.warning("hallmark_seed_file_missing path=%s", path)
            return set()
        payload = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
        return {normalize_label(str(x)) for x in payload.get("hallmarks", [])}

    def normalize_and_filter_backbone_items(self, combined: Dict[str, list]) -> Tuple[Dict[str, list], Dict[str, list]]:
        review_queue: Dict[str, list] = defaultdict(list)

        hallmarks: List[HallmarkCandidate] = []
        for hallmark in combined.get("hallmarks", []):
            norm = merge_synonym_label(normalize_label(hallmark.label))
            if norm == "unknown hallmark" or norm == "unknown_hallmark" or (self.hallmark_seeds and norm not in self.hallmark_seeds):
                hallmark.status = "review"
                review_queue["hallmarks"].append(hallmark)
                continue
            hallmark.normalized_label = norm
            hallmarks.append(hallmark)

        modules: List[ModuleCandidate] = []
        for module in combined.get("modules", []):
            module.label = module.label.strip()
            module.normalized_label = merge_synonym_label(normalize_label(module.label))
            module.key_genes = [g for g in module.key_genes if g]
            module.evidence_count = max(module.evidence_count, len(set(module.supporting_source_packet_ids)))
            lowered = module.normalized_label.lower()
            if any(x in lowered for x in _PHENOTYPE_TERMS):
                module.module_type = "phenotype_module"
                module.mechanism_category = "phenotype"
            if any(x in lowered for x in _NOISE_TERMS):
                module.module_type = "supporting_module"
                module.mechanism_category = "intervention"
                module.status = "review"
                review_queue["modules"].append(module)
                modules.append(module)
                continue
            if any(x in lowered for x in _INTERVENTION_TERMS) and module.module_type == "core_mechanism_module":
                module.module_type = "supporting_module"
                module.mechanism_category = "intervention"
            if module.module_type == "core_mechanism_module" and (
                not module.description.strip() or not module.key_genes or not module.process_terms
            ):
                module.status = "provisional"
                review_queue["modules"].append(module)
            modules.append(module)

        relations = []
        for rel in combined.get("relations", []):
            if not rel.subject_module.strip() or not rel.object_module.strip():
                review_queue["relations"].append(rel)
                continue
            relations.append(rel)

        genes = []
        for gene in combined.get("genes", []):
            if not gene.symbol.strip():
                gene.status = "review"
                review_queue["genes"].append(gene)
                continue
            genes.append(gene)

        refined = {**combined, "hallmarks": hallmarks, "modules": modules, "relations": relations, "genes": genes}
        return refined, review_queue

    def deduplicate_modules(self, modules: List[ModuleCandidate]) -> List[ModuleCandidate]:
        by_key: Dict[str, ModuleCandidate] = {}
        for module in modules:
            key = module.normalized_label
            if key not in by_key:
                by_key[key] = module
                continue
            current = by_key[key]
            current.supporting_source_packet_ids = sorted(set(current.supporting_source_packet_ids + module.supporting_source_packet_ids))
            current.supporting_source_document_ids = sorted(set(current.supporting_source_document_ids + module.supporting_source_document_ids))
            current.key_genes = sorted(set(current.key_genes + module.key_genes))
            current.process_terms = sorted(set(current.process_terms + module.process_terms))
            current.evidence_count += module.evidence_count
            current.candidate_confidence = max(current.candidate_confidence, module.candidate_confidence)

        deduped = []
        for idx, module in enumerate(sorted(by_key.values(), key=lambda x: x.normalized_label), start=1):
            digest = hashlib.md5(module.normalized_label.encode("utf-8")).hexdigest()[:8]
            module.candidate_id = f"mod_{idx:03d}_{digest}"
            deduped.append(module)
        return deduped

    def bind_genes_to_modules(self, modules: List[ModuleCandidate], genes: List[KeyGeneCandidate]) -> List[KeyGeneCandidate]:
        module_by_gene: Dict[str, Set[str]] = defaultdict(set)
        for module in modules:
            for symbol in module.key_genes:
                module_by_gene[symbol].add(module.normalized_label)

        for gene in genes:
            links = set(gene.linked_modules) | module_by_gene.get(gene.symbol, set())
            if not links and gene.symbol in _CORE_PD_GENES:
                inferred = [m.normalized_label for m in modules if gene.symbol in m.key_genes]
                links.update(inferred)
            gene.linked_modules = sorted(links)
            if gene.symbol in _CORE_PD_GENES and gene.gene_role == "uncertain":
                gene.gene_role = "driver"
            if not gene.linked_modules:
                gene.status = "provisional"
        return genes

    def score_modules(self, modules: List[ModuleCandidate], relations: List, chains: List[CausalChainCandidate]) -> None:
        relation_nodes = {r.subject_module for r in relations} | {r.object_module for r in relations}
        chain_nodes = {normalize_label(step.event_label) for c in chains for step in c.steps}
        for module in modules:
            score = 0.15
            score += min(0.3, 0.08 * len(set(module.supporting_source_packet_ids)))
            if module.normalized_label in self.hallmark_seeds:
                score += 0.2
            if module.key_genes:
                score += 0.15
            if module.process_terms:
                score += 0.1
            if module.normalized_label in relation_nodes or module.normalized_label in chain_nodes:
                score += 0.1
            if module.module_type == "phenotype_module" or module.mechanism_category == "intervention":
                score -= 0.2
            module.candidate_confidence = round(max(0.01, min(1.0, score)), 4)

    def build_canonical_chains(self, modules: List[ModuleCandidate], genes: List[KeyGeneCandidate], relations: List) -> List[CausalChainCandidate]:
        packets = sorted({sid for m in modules for sid in m.supporting_source_packet_ids})
        chain_specs = [
            ["gene/variant perturbation", "alpha-synuclein aggregation", "lysosomal/autophagy dysfunction", "neuronal vulnerability", "motor phenotype"],
            ["gene/variant perturbation", "mitochondrial dysfunction", "oxidative stress", "dopaminergic neuron degeneration", "motor phenotype"],
            ["gene/variant perturbation", "neuroinflammation", "neuronal dysfunction", "non-motor phenotype"],
        ]
        chains: List[CausalChainCandidate] = []
        for idx, events in enumerate(chain_specs, start=1):
            steps = [CausalStep(order=i, event_label=evt) for i, evt in enumerate(events, start=1)]
            chains.append(
                CausalChainCandidate(
                    candidate_id=f"chain_v2_{idx:03d}",
                    title=f"pd_canonical_chain_{idx}",
                    module_label="parkinson_mechanism",
                    steps=steps,
                    supporting_source_packet_ids=packets,
                    supporting_source_document_ids=[],
                    candidate_confidence=0.8,
                    status="candidate",
                )
            )
        return chains
