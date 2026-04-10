from __future__ import annotations

from typing import Dict, Set


class GeneNormalizer:
    def __init__(self) -> None:
        self.alias_to_symbol: Dict[str, str] = {
            "snca": "SNCA",
            "alpha-synuclein": "SNCA",
            "α-synuclein": "SNCA",
            "α-synuclein": "SNCA",
            "Α-SYNUCLEIN".lower(): "SNCA",
            "dj-1": "PARK7",
            "park7": "PARK7",
            "pink-1": "PINK1",
            "pink1": "PINK1",
        }
        self.unresolved_aliases: Set[str] = set()

    def normalize(self, symbol: str) -> str:
        raw = (symbol or "").strip()
        if not raw:
            return ""
        key = raw.lower()
        if key in self.alias_to_symbol:
            return self.alias_to_symbol[key]
        if raw.upper().replace("-", "").isalnum() and len(raw) <= 10:
            return raw.upper().replace("-", "")
        self.unresolved_aliases.add(raw)
        return raw.upper()
