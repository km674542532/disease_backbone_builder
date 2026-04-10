from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from app.schemas.candidates import CausalChainCandidate, CausalStep, HallmarkCandidate, KeyGeneCandidate, ModuleCandidate, ModuleRelation


@dataclass
class GraphEdge:
    src: str
    dst: str
    predicate: str
    edge_confidence: float
    supporting_source_packet_ids: List[str]
    mechanism_category: str


def score_graph_edge(source_weight_sum: float, support_count: int, relation_confidence: float) -> float:
    score = 0.2 + min(0.4, source_weight_sum * 0.2) + min(0.2, support_count * 0.05) + relation_confidence * 0.2
    return round(max(0.05, min(1.0, score)), 4)


def build_backbone_graph(
    hallmarks: List[HallmarkCandidate], modules: List[ModuleCandidate], genes: List[KeyGeneCandidate], relations: List[ModuleRelation]
) -> Tuple[Dict[str, str], List[GraphEdge], Dict[str, Set[str]]]:
    node_type: Dict[str, str] = {}
    for h in hallmarks:
        node_type[h.normalized_label] = "hallmark"
    for m in modules:
        node_type[m.normalized_label] = "module"
    for g in genes:
        node_type[g.normalized_symbol or g.symbol] = "gene"
    adjacency: Dict[str, Set[str]] = defaultdict(set)
    edges: List[GraphEdge] = []

    for m in modules:
        for g in m.key_genes:
            edge = GraphEdge(g, m.normalized_label, "supports", m.candidate_confidence, m.supporting_source_packet_ids, m.mechanism_category)
            edges.append(edge)
            adjacency[g].add(m.normalized_label)
    for m in modules:
        for hl in m.hallmark_links:
            edge = GraphEdge(m.normalized_label, hl, "converges_on", m.candidate_confidence, m.supporting_source_packet_ids, m.mechanism_category)
            edges.append(edge)
            adjacency[m.normalized_label].add(hl)
    for r in relations:
        edge = GraphEdge(r.subject_module, r.object_module, r.predicate, r.candidate_confidence, r.supporting_source_packet_ids, r.mechanism_category)
        edges.append(edge)
        adjacency[r.subject_module].add(r.object_module)
    return node_type, edges, adjacency


def enumerate_candidate_chains(adjacency: Dict[str, Set[str]], starts: List[str], max_depth: int = 6) -> List[List[str]]:
    chains: List[List[str]] = []
    for start in starts:
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            if len(path) >= 3:
                chains.append(path)
            if len(path) >= max_depth:
                continue
            for nxt in adjacency.get(node, set()):
                if nxt in path:
                    continue
                stack.append((nxt, path + [nxt]))
    return chains


def rank_canonical_chains(candidate_paths: List[List[str]], edge_map: Dict[Tuple[str, str], GraphEdge], node_conf: Dict[str, float]) -> List[Tuple[List[str], float, Dict[str, float]]]:
    ranked = []
    for path in candidate_paths:
        source_weight_sum = 0.0
        edge_confidence_sum = 0.0
        unsupported_hop_penalty = 0.0
        supporting_sources: Set[str] = set()
        categories: Set[str] = set()
        for src, dst in zip(path[:-1], path[1:]):
            edge = edge_map.get((src, dst))
            if not edge:
                unsupported_hop_penalty += 0.1
                continue
            edge_confidence_sum += edge.edge_confidence
            source_weight_sum += edge.edge_confidence
            supporting_sources.update(edge.supporting_source_packet_ids)
            if edge.mechanism_category:
                categories.add(edge.mechanism_category)
        node_confidence_sum = sum(node_conf.get(n, 0.1) for n in path)
        disease_specificity_bonus = 0.1 if any("parkinson" in n.lower() or "alpha" in n.lower() for n in path) else 0.0
        noise_penalty = 0.05 if any("intervention" in n for n in path) else 0.0
        total = source_weight_sum + node_confidence_sum + edge_confidence_sum + disease_specificity_bonus - unsupported_hop_penalty - noise_penalty
        conf = max(0.05, min(1.0, total / max(3.0, len(path) * 1.2)))
        ranked.append((path, round(conf, 4), {
            "source_support_score": round(source_weight_sum, 4),
            "source_diversity_score": round(min(1.0, len(supporting_sources) / 5), 4),
            "normalization_score": 1.0,
            "structural_completeness_score": round(min(1.0, len(path) / 6), 4),
            "chain_connectivity_score": round(min(1.0, edge_confidence_sum / max(1, len(path) - 1)), 4),
            "penalty_score": round(unsupported_hop_penalty + noise_penalty, 4),
        }))
    return sorted(ranked, key=lambda x: x[1], reverse=True)


def build_chains_from_graph(
    hallmarks: List[HallmarkCandidate], modules: List[ModuleCandidate], genes: List[KeyGeneCandidate], relations: List[ModuleRelation]
) -> List[CausalChainCandidate]:
    node_type, edges, adjacency = build_backbone_graph(hallmarks, modules, genes, relations)
    edge_map = {(e.src, e.dst): e for e in edges}
    starts = [g.normalized_symbol or g.symbol for g in genes if g.status == "candidate"] + [m.normalized_label for m in modules if m.status == "candidate"]
    starts = list(dict.fromkeys(starts))
    candidates = enumerate_candidate_chains(adjacency, starts)
    node_conf = {**{m.normalized_label: m.candidate_confidence for m in modules}, **{h.normalized_label: h.candidate_confidence for h in hallmarks}}
    ranked = rank_canonical_chains(candidates, edge_map, node_conf)
    output: List[CausalChainCandidate] = []
    for idx, (path, score, breakdown) in enumerate(ranked[:8], start=1):
        steps = [CausalStep(order=i, event_label=n, step_type=node_type.get(n, "module")) for i, n in enumerate(path, start=1)]
        sources = sorted({sid for s, d in zip(path[:-1], path[1:]) for sid in edge_map.get((s, d), GraphEdge('', '', '', 0, [], '')).supporting_source_packet_ids})
        output.append(CausalChainCandidate(
            candidate_id=f"chain_v3_{idx:03d}",
            title=f"pd_graph_chain_{idx}",
            module_label="parkinson_mechanism_graph",
            steps=steps,
            supporting_source_packet_ids=sources,
            source_diversity_count=len(sources),
            dominant_mechanism_categories=sorted({edge_map[(s,d)].mechanism_category for s,d in zip(path[:-1], path[1:]) if (s,d) in edge_map and edge_map[(s,d)].mechanism_category}),
            candidate_confidence=score,
            confidence_breakdown=breakdown,
            status="candidate",
        ))
    return output
