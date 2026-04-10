"""Lightweight ontology/synonym mapping helpers."""
from __future__ import annotations

_GENE_ALIAS = {
    "Α-SYNUCLEIN": "SNCA",
    "ALPHA-SYNUCLEIN": "SNCA",
    "DJ-1": "PARK7",
    "DJ1": "PARK7",
    "PARK7": "PARK7",
    "LRRK-2": "LRRK2",
}

_LABEL_SYNONYMS = {
    "alpha synuclein aggregation": "alpha-synuclein aggregation",
    "α synuclein aggregation": "alpha-synuclein aggregation",
    "mitochondrial dysfunction": "mitochondrial dysfunction",
    "lysosomal autophagy dysfunction": "lysosomal/autophagy dysfunction",
    "dopaminergic neuron loss": "dopaminergic neuron degeneration",
}


def map_gene_to_hgnc(symbol: str) -> str:
    """Map common aliases to canonical HGNC-like symbols."""
    cleaned = (symbol or "").strip().upper()
    if not cleaned:
        return ""
    return _GENE_ALIAS.get(cleaned, cleaned)


def merge_synonym_label(label: str) -> str:
    """Apply a small synonym table for stable normalization."""
    cleaned = (label or "").strip().lower()
    return _LABEL_SYNONYMS.get(cleaned, cleaned)
