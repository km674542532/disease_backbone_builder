from __future__ import annotations

from typing import Dict


class PhenotypeNormalizer:
    def __init__(self) -> None:
        self.map: Dict[str, str] = {
            "motor symptoms": "motor_symptoms",
            "gait impairment": "gait_impairment",
            "mood disorders": "mood_disorders",
            "urogenital dysfunction": "urogenital_dysfunction",
            "non-motor": "non_motor_phenotype",
            "motor phenotype": "motor_symptoms",
        }

    def normalize(self, label: str) -> str:
        lowered = (label or "").lower()
        for k, v in self.map.items():
            if k in lowered:
                return v
        return ""
