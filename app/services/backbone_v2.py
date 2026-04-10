"""Production-oriented backbone v3 refinement layer (kept in backbone_v2.py for CLI compatibility)."""
from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml

from app.core.normalization import HGNCGeneNormalizer, MultiSourceDiseaseNormalizer, NormalizationQACollector
from app.normalization import MechanismNormalizer, PhenotypeNormalizer
from app.schemas.candidates import CausalChainCandidate, HallmarkCandidate, KeyGeneCandidate, ModuleCandidate
from app.services.v3.graph_chain_builder import build_chains_from_graph
from app.services.v3.source_quality import TIER_WEIGHTS
from app.utils.ontology_mapper import merge_synonym_label
from app.utils.text_normalize import normalize_label

logger = logging.getLogger(__name__)

_NOISE_TERMS = {"dance", "walking", "tdcs", "quality of life", "clinical management", "management"}
_HIGH_WEIGHT = 0.8


class BackboneV2Refiner:
    def __init__(self, seed_path: str = "data/seeds/pd_hallmark_seeds.yaml") -> None:
        self.seed_path = seed_path
        self.hallmark_seeds = self._load_hallmark_seeds(seed_path)
        self.gene_normalizer = HGNCGeneNormalizer("data/standards/hgnc/hgnc_complete_set.json")
        self.disease_normalizer = MultiSourceDiseaseNormalizer(
            "data/standards/mondo/mondo_snapshot.json",
            "data/standards/mesh/mesh_snapshot.json",
            "data/standards/orphanet/orphanet_snapshot.json",
        )
        self.mechanism_normalizer = MechanismNormalizer()
        self.phenotype_normalizer = PhenotypeNormalizer()
        self.qa_collector = NormalizationQACollector()

    def _load_hallmark_seeds(self, path: str) -> Set[str]:
        fp = Path(path)
        if not fp.exists():
            logger.warning("hallmark_seed_file_missing path=%s", path)
            return set()
        payload = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
        return {normalize_label(str(x)) for x in payload.get("hallmarks", [])}

    def _source_weight(self, packet_ids: List[str], packet_quality: Dict[str, Dict[str, float | str]]) -> Tuple[float, int, float]:
        unique = sorted(set(packet_ids))
        weights = [float(packet_quality.get(pid, {}).get("source_weight", 0.2)) for pid in unique]
        high = max(weights) if weights else 0.0
        return round(sum(weights), 4), len(unique), high

    def _confidence_breakdown(self, *, source_support: float, diversity: int, normalization_score: float, structural: float, connectivity: float, penalty: float) -> Dict[str, float]:
        return {
            "source_support_score": round(source_support, 4),
            "source_diversity_score": round(min(1.0, diversity / 5), 4),
            "normalization_score": round(normalization_score, 4),
            "structural_completeness_score": round(structural, 4),
            "chain_connectivity_score": round(connectivity, 4),
            "penalty_score": round(penalty, 4),
        }

    def normalize_and_filter_backbone_items(
        self, combined: Dict[str, list], packet_quality: Dict[str, Dict[str, float | str]]
    ) -> Tuple[Dict[str, list], Dict[str, list], Dict[str, int]]:
        review_queue: Dict[str, list] = defaultdict(list)
        metrics = {"promoted_core_item_count": 0, "demoted_low_evidence_item_count": 0}

        hallmarks: List[HallmarkCandidate] = []
        for hallmark in combined.get("hallmarks", []):
            norm = merge_synonym_label(normalize_label(hallmark.label))
            hallmark.normalized_label = norm
            hallmark.normalized_category = self.mechanism_normalizer.normalize(norm)
            source_support, diversity, high_weight = self._source_weight(hallmark.supporting_source_packet_ids, packet_quality)
            hallmark.source_weighted_support = source_support
            is_seed_or_expanded = norm in self.hallmark_seeds or any(seed in norm or norm in seed for seed in self.hallmark_seeds)
            if not is_seed_or_expanded:
                hallmark.status = "review"
                review_queue["hallmarks"].append(hallmark)
                continue
            if diversity < 2 or high_weight < 0.45:
                hallmark.status = "provisional"
                metrics["demoted_low_evidence_item_count"] += 1
            else:
                hallmark.status = "core-draft"
                metrics["promoted_core_item_count"] += 1
            breakdown = self._confidence_breakdown(
                source_support=source_support,
                diversity=diversity,
                normalization_score=1.0,
                structural=1.0 if hallmark.description.strip() else 0.5,
                connectivity=0.6,
                penalty=0.2 if hallmark.status == "provisional" else 0.0,
            )
            hallmark.confidence_breakdown = breakdown
            hallmark.candidate_confidence = round(max(0.05, min(1.0, (sum(breakdown.values()) - breakdown["penalty_score"]) / 5)), 4)
            hallmarks.append(hallmark)

        modules: List[ModuleCandidate] = []
        for module in combined.get("modules", []):
            module.normalized_label = merge_synonym_label(normalize_label(module.label.strip()))
            module.normalized_category = self.mechanism_normalizer.normalize(f"{module.normalized_label} {module.mechanism_category}")
            if self.phenotype_normalizer.normalize(module.label):
                module.module_type = "phenotype_module"
                module.mechanism_category = "phenotype"
            normalized_genes = []
            for g in module.key_genes:
                if not g:
                    continue
                result = self.gene_normalizer.normalize(g)
                self.qa_collector.add_gene(result)
                normalized_genes.append(result.normalized_label or g.upper())
                if "unresolved" in result.qa_flags or "low_confidence" in result.qa_flags:
                    module.status = "provisional"
                    review_queue["modules"].append(module)
            module.key_genes = sorted(set(normalized_genes))
            module.process_terms = sorted({p.strip() for p in module.process_terms if p.strip()})
            if any(x in module.normalized_label for x in _NOISE_TERMS):
                module.status = "review"
                review_queue["modules"].append(module)
                continue
            source_support, diversity, high_weight = self._source_weight(module.supporting_source_packet_ids, packet_quality)
            module.evidence_count = max(module.evidence_count, diversity)
            module.source_diversity_count = diversity
            module.weighted_support_score = source_support
            structural = 1.0 if module.description.strip() and module.key_genes and module.process_terms else 0.4
            core_eligible = diversity >= 2 or (high_weight >= _HIGH_WEIGHT and structural >= 0.9)
            if module.module_type == "core_mechanism_module" and core_eligible:
                module.status = "core-draft"
                metrics["promoted_core_item_count"] += 1
            elif module.module_type == "core_mechanism_module":
                module.status = "provisional"
                metrics["demoted_low_evidence_item_count"] += 1
                review_queue["modules"].append(module)
            breakdown = self._confidence_breakdown(
                source_support=source_support,
                diversity=diversity,
                normalization_score=1.0,
                structural=structural,
                connectivity=0.7,
                penalty=0.25 if module.status == "provisional" else 0.0,
            )
            module.confidence_breakdown = breakdown
            module.candidate_confidence = round(max(0.05, min(1.0, (sum(breakdown.values()) - breakdown["penalty_score"]) / 5)), 4)
            modules.append(module)

        relations = []
        for rel in combined.get("relations", []):
            if not rel.subject_module.strip() or not rel.object_module.strip():
                review_queue["relations"].append(rel)
                continue
            rel.mechanism_category = self.mechanism_normalizer.normalize(rel.description)
            source_support, diversity, _ = self._source_weight(rel.supporting_source_packet_ids, packet_quality)
            rel.edge_confidence = round(max(0.05, min(1.0, rel.candidate_confidence * 0.6 + source_support * 0.2 + min(0.2, diversity * 0.05))), 4)
            rel.confidence_breakdown = self._confidence_breakdown(
                source_support=source_support,
                diversity=diversity,
                normalization_score=1.0,
                structural=1.0,
                connectivity=rel.edge_confidence,
                penalty=0.0,
            )
            relations.append(rel)

        genes = []
        for gene in combined.get("genes", []):
            if not gene.symbol.strip():
                gene.status = "review"
                review_queue["genes"].append(gene)
                continue
            norm_result = self.gene_normalizer.normalize(gene.symbol)
            self.qa_collector.add_gene(norm_result)
            gene.normalized_symbol = norm_result.normalized_label or gene.symbol
            gene.hgnc_id = str(norm_result.metadata.get("hgnc_id", ""))
            gene.approved_name = str(norm_result.metadata.get("approved_name", ""))
            gene.match_type = norm_result.match_type
            gene.source_authority = norm_result.source_authority
            gene.source_version = norm_result.source_version
            source_support, diversity, _ = self._source_weight(gene.supporting_source_packet_ids, packet_quality)
            if not gene.rationale.strip() or "unresolved" in norm_result.qa_flags or "low_confidence" in norm_result.qa_flags:
                gene.status = "provisional"
                review_queue["genes"].append(gene)
            elif gene.status == "candidate":
                gene.status = "core-draft"
            gene.confidence_breakdown = self._confidence_breakdown(
                source_support=source_support,
                diversity=diversity,
                normalization_score=1.0 if gene.normalized_symbol != gene.symbol or gene.symbol.isupper() else 0.7,
                structural=1.0 if gene.rationale.strip() else 0.4,
                connectivity=0.7,
                penalty=0.2 if gene.status == "provisional" else 0.0,
            )
            gene.candidate_confidence = round(max(0.05, min(1.0, (sum(gene.confidence_breakdown.values()) - gene.confidence_breakdown["penalty_score"]) / 5)), 4)
            genes.append(gene)

        refined = {**combined, "hallmarks": hallmarks, "modules": modules, "relations": relations, "genes": genes}
        return refined, review_queue, metrics

    def deduplicate_modules(self, modules: List[ModuleCandidate]) -> List[ModuleCandidate]:
        by_key: Dict[str, ModuleCandidate] = {}
        for module in modules:
            key = f"{module.normalized_label}::{module.normalized_category}"
            if key not in by_key:
                by_key[key] = module
                continue
            current = by_key[key]
            current.supporting_source_packet_ids = sorted(set(current.supporting_source_packet_ids + module.supporting_source_packet_ids))
            current.supporting_source_document_ids = sorted(set(current.supporting_source_document_ids + module.supporting_source_document_ids))
            current.key_genes = sorted(set(current.key_genes + module.key_genes))
            current.process_terms = sorted(set(current.process_terms + module.process_terms))
            current.hallmark_links = sorted(set(current.hallmark_links + module.hallmark_links))
            current.evidence_count = max(current.evidence_count, module.evidence_count)
            current.weighted_support_score = max(current.weighted_support_score, module.weighted_support_score)
            current.candidate_confidence = max(current.candidate_confidence, module.candidate_confidence)

        deduped = []
        for idx, module in enumerate(sorted(by_key.values(), key=lambda x: x.normalized_label), start=1):
            digest = hashlib.md5(f"{module.normalized_label}::{module.normalized_category}".encode("utf-8")).hexdigest()[:8]
            module.candidate_id = f"mod_{idx:03d}_{digest}"
            deduped.append(module)
        return deduped

    def bind_genes_to_modules(self, modules: List[ModuleCandidate], genes: List[KeyGeneCandidate]) -> List[KeyGeneCandidate]:
        module_by_gene: Dict[str, Set[str]] = defaultdict(set)
        category_by_gene: Dict[str, Set[str]] = defaultdict(set)
        for module in modules:
            for symbol in module.key_genes:
                module_by_gene[symbol].add(module.normalized_label)
                category_by_gene[symbol].add(module.normalized_category or module.mechanism_category)

        for gene in genes:
            key = gene.normalized_symbol or gene.symbol
            gene.linked_modules = sorted(set(gene.linked_modules) | module_by_gene.get(key, set()))
            gene.supporting_mechanism_categories = sorted(category_by_gene.get(key, set()))
            if gene.linked_modules and gene.gene_role == "uncertain":
                gene.gene_role = "driver"
            if not gene.linked_modules:
                gene.status = "provisional"
        return genes

    def build_canonical_chains(self, hallmarks: List[HallmarkCandidate], modules: List[ModuleCandidate], genes: List[KeyGeneCandidate], relations: List) -> List[CausalChainCandidate]:
        chains = build_chains_from_graph(hallmarks, modules, genes, relations)
        return chains[: max(3, min(8, len(chains)))]

    def disease_ids_v3(self, disease_label: str, ids: Dict[str, str | None]) -> Dict[str, str | None]:
        result = self.disease_normalizer.normalize(disease_label)
        self.qa_collector.add_disease(result)
        merged = dict(ids)
        merged.update(result.ids)
        return merged

    def unresolved_aliases(self) -> List[str]:
        return sorted({x.raw_input for x in self.qa_collector.gene_results if "unresolved" in x.qa_flags or x.match_type == "unresolved"})

    def weighted_support_summary(self, packet_quality: Dict[str, Dict[str, float | str]]) -> Dict[str, float]:
        vals = [float(v.get("source_weight", 0.2)) for v in packet_quality.values()]
        if not vals:
            return {"avg_source_weight": 0.0, "max_source_weight": 0.0, "tier_weight_count": 0.0}
        return {
            "avg_source_weight": round(sum(vals) / len(vals), 4),
            "max_source_weight": round(max(vals), 4),
            "tier_weight_count": round(sum(TIER_WEIGHTS.values()), 4),
        }

    def normalization_reports(self) -> Dict[str, object]:
        return {
            "qa_report": {
                "gene": self.qa_collector.gene_metrics(),
                "disease": self.qa_collector.disease_metrics(),
            },
            "unresolved_items": self.qa_collector.unresolved_items(),
            "conflicts": self.qa_collector.conflicts(),
        }
