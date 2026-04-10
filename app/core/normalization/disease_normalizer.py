from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.core.normalization.base import DiseaseNormalizationPayload
from app.core.normalization.local_cache import LocalStandardCache
from app.core.normalization.resolver_utils import fuzzy_candidates, normalize_token


class MultiSourceDiseaseNormalizer:
    def __init__(self, mondo_file: str, mesh_file: str, orphanet_file: str, cache: LocalStandardCache | None = None) -> None:
        self.cache = cache or LocalStandardCache()
        self.mondo_records = self.cache.load_json_records("MONDO", mondo_file)
        self.mesh_records = self.cache.load_json_records("MeSH", mesh_file)
        self.orpha_records = self.cache.load_json_records("Orphanet", orphanet_file)
        self.meta = {
            "MONDO": self.cache.metadata("MONDO", mondo_file),
            "MeSH": self.cache.metadata("MeSH", mesh_file),
            "Orphanet": self.cache.metadata("Orphanet", orphanet_file),
        }

    def normalize(self, disease_label: str) -> DiseaseNormalizationPayload:
        query = normalize_token(disease_label)
        mondo = self._match_source(query, self.mondo_records, label_key="label", id_key="id", synonyms_key="synonyms")
        mesh = self._match_source(query, self.mesh_records, label_key="label", id_key="descriptor_id", synonyms_key="aliases")
        orpha = self._match_source(query, self.orpha_records, label_key="label", id_key="orpha_code", synonyms_key="synonyms")

        qa_flags: List[str] = []
        conflict: Optional[str] = None
        source_used: List[str] = []
        synonyms: List[str] = []
        if mondo[0]:
            source_used.append("MONDO")
            synonyms.extend(mondo[0].get("synonyms", []) or [])
        if mesh[0]:
            source_used.append("MeSH")
            synonyms.extend(mesh[0].get("aliases", []) or [])
        if orpha[0]:
            source_used.append("Orphanet")
            synonyms.extend(orpha[0].get("synonyms", []) or [])

        if not any([mondo[0], mesh[0], orpha[0]]):
            qa_flags.append("unresolved")

        if any(flag == "fuzzy_only" for flag in mondo[1] + mesh[1] + orpha[1]):
            qa_flags.extend(["fuzzy_only", "low_confidence"])

        labels = [str(x[0].get("label", "")) for x in (mondo, mesh, orpha) if x[0]]
        if labels and len(set(normalize_token(x) for x in labels)) > 1:
            conflict = f"label_conflict: {labels}"
            qa_flags.append("authority_conflict")

        normalized_label = labels[0] if labels else disease_label
        return DiseaseNormalizationPayload(
            normalized_label=normalized_label,
            ids={
                "mondo": str(mondo[0].get("id")) if mondo[0] else None,
                "mesh": str(mesh[0].get("descriptor_id")) if mesh[0] else None,
                "orphanet": str(orpha[0].get("orpha_code")) if orpha[0] else None,
                "omim": str(mondo[0].get("omim")) if mondo[0] and mondo[0].get("omim") else None,
            },
            synonyms=sorted(set(synonyms)),
            source_authorities_used=source_used,
            conflict=conflict,
            qa_flags=sorted(set(qa_flags + mondo[1] + mesh[1] + orpha[1])),
        )

    def _match_source(
        self,
        query: str,
        records: List[Dict[str, object]],
        *,
        label_key: str,
        id_key: str,
        synonyms_key: str,
    ) -> Tuple[Optional[Dict[str, object]], List[str]]:
        if not records:
            return None, ["unresolved"]
        for record in records:
            if normalize_token(str(record.get(label_key, ""))) == query:
                return record, []
        for record in records:
            syns = [normalize_token(str(x)) for x in (record.get(synonyms_key, []) or [])]
            if query in syns:
                return record, ["alias_match"]

        labels = [str(r.get(label_key, "")) for r in records]
        fuzzy = fuzzy_candidates(query, labels, threshold=0.9)
        if len(fuzzy) == 1:
            chosen = fuzzy[0][0]
            rec = next((r for r in records if str(r.get(label_key, "")) == chosen), None)
            return rec, ["fuzzy_only"] if rec else ["unresolved"]
        if len(fuzzy) > 1:
            return None, ["multiple_candidates", "authority_conflict", "low_confidence"]
        return None, ["unresolved"]
