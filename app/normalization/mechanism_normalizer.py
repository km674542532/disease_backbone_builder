from __future__ import annotations

from typing import Dict


class MechanismNormalizer:
    def __init__(self) -> None:
        self.rule_map: Dict[str, str] = {
            "alpha-synuclein": "alpha_synuclein",
            "snca": "alpha_synuclein",
            "mitochond": "mitochondrial",
            "lysosom": "lysosome_autophagy",
            "autophagy": "lysosome_autophagy",
            "inflamm": "neuroinflammation",
            "oxidative": "oxidative_stress",
            "synap": "synaptic",
            "vesicle": "vesicle_trafficking",
            "proteostasis": "proteostasis",
            "metal": "metal_homeostasis",
            "gut": "gut_brain_axis",
            "dopaminergic": "dopaminergic_neuron_vulnerability",
            "phenotype": "phenotype",
            "biomarker": "biomarker",
            "intervention": "intervention",
        }

    def normalize(self, text: str) -> str:
        lowered = (text or "").lower()
        for needle, category in self.rule_map.items():
            if needle in lowered:
                return category
        return "proteostasis"
