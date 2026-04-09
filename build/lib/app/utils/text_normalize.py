"""Text normalization utilities used by normalizer service."""
from __future__ import annotations

import re
import string


_WS_RE = re.compile(r"\s+")


def normalize_whitespace(value: str) -> str:
    return _WS_RE.sub(" ", value).strip()


def strip_punctuation(value: str) -> str:
    table = str.maketrans("", "", string.punctuation)
    return value.translate(table)


def normalize_label(value: str) -> str:
    return normalize_whitespace(strip_punctuation(value.lower()))


def normalize_gene_symbol(value: str) -> str:
    return normalize_whitespace(value).upper()
