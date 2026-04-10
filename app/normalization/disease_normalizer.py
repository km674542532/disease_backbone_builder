from __future__ import annotations

from typing import Dict


class DiseaseNormalizer:
    def normalize(self, disease_label: str, ids: Dict[str, str | None] | None = None) -> Dict[str, str | None]:
        normalized = dict(ids or {})
        label = (disease_label or "").lower()
        if "parkinson" in label:
            normalized.setdefault("mondo", "MONDO:0005180")
            normalized.setdefault("mesh", "D010300")
            normalized.setdefault("orphanet", "ORPHA:282")
            normalized.setdefault("omim", "168600")
        else:
            normalized.setdefault("mondo", "MONDO:UNKNOWN")
            normalized.setdefault("mesh", None)
            normalized.setdefault("orphanet", None)
            normalized.setdefault("omim", None)
        return normalized
