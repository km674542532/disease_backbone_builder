from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Iterable, List, Tuple

_GREEK_MAP = {
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "Α": "alpha",
    "Β": "beta",
}


def normalize_token(text: str) -> str:
    value = unicodedata.normalize("NFKC", (text or "").strip())
    for src, target in _GREEK_MAP.items():
        value = value.replace(src, target)
    value = value.lower().replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def fuzzy_candidates(query: str, candidates: Iterable[str], threshold: float = 0.86) -> List[Tuple[str, float]]:
    out: List[Tuple[str, float]] = []
    nq = normalize_token(query)
    for cand in candidates:
        score = SequenceMatcher(None, nq, normalize_token(cand)).ratio()
        if score >= threshold:
            out.append((cand, round(score, 4)))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
