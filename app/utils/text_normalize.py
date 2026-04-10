"""Text normalization utilities used by normalizer service."""
from __future__ import annotations

import re
import string


_WS_RE = re.compile(r"\s+")


_GREEK_REPLACEMENTS = {
    "Α": "A",
    "α": "A",
    "Β": "B",
    "β": "B",
}


def normalize_whitespace(value: str) -> str:
    return _WS_RE.sub(" ", value).strip()


def strip_punctuation(value: str) -> str:
    table = str.maketrans("", "", string.punctuation)
    return value.translate(table)


def normalize_label(value: str) -> str:
    return normalize_whitespace(strip_punctuation(value.lower()))


def normalize_gene_symbol(value: str) -> str:
    txt = normalize_whitespace(value)
    for src, dst in _GREEK_REPLACEMENTS.items():
        txt = txt.replace(src, dst)
    txt = txt.replace(" ", "").replace("_", "-")
    return txt.upper()
