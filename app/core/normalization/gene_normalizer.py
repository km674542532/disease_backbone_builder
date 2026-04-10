from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from app.core.normalization.base import NormalizationCandidate, NormalizationResult
from app.core.normalization.local_cache import LocalStandardCache
from app.core.normalization.resolver_utils import fuzzy_candidates, normalize_token


class HGNCGeneNormalizer:
    def __init__(self, hgnc_file: str, cache: LocalStandardCache | None = None) -> None:
        self.hgnc_file = hgnc_file
        self.cache = cache or LocalStandardCache()
        self.records = self.cache.load_json_records("HGNC", hgnc_file)
        self.meta = self.cache.metadata("HGNC", hgnc_file)
        self.by_symbol: Dict[str, Dict[str, object]] = {}
        self.by_alias: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        self.by_prev_symbol: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        self._build_indexes()

    def _build_indexes(self) -> None:
        for record in self.records:
            symbol = str(record.get("symbol", "")).upper().strip()
            if not symbol:
                continue
            self.by_symbol[symbol] = record
            self.by_symbol[normalize_token(symbol).upper()] = record
            for alias in record.get("alias_symbol", []) or []:
                self.by_alias[normalize_token(str(alias))].append(record)
            for prev in record.get("prev_symbol", []) or []:
                self.by_prev_symbol[normalize_token(str(prev))].append(record)

    def normalize(self, raw_symbol: str) -> NormalizationResult:
        raw = (raw_symbol or "").strip()
        lookup_symbol = raw.upper().replace("-", "")
        alias_key = normalize_token(raw)
        qa_flags: List[str] = []

        record = self.by_symbol.get(raw.upper()) or self.by_symbol.get(lookup_symbol)
        if record:
            return self._to_result(raw, record, "exact", 0.99, qa_flags)

        alias_hits = self.by_alias.get(alias_key, [])
        alias_hits = list({str(x.get("symbol", "")): x for x in alias_hits}.values())
        if len(alias_hits) == 1:
            if raw.upper() in {"DJ-1", "PINK-1"}:
                qa_flags.append("deprecated_symbol_used")
            return self._to_result(raw, alias_hits[0], "alias", 0.95, qa_flags, matched_alias=raw)
        if len(alias_hits) > 1:
            qa_flags.append("multiple_candidates")
            return self._ambiguous(raw, alias_hits, qa_flags)

        prev_hits = self.by_prev_symbol.get(alias_key, [])
        prev_hits = list({str(x.get("symbol", "")): x for x in prev_hits}.values())
        if len(prev_hits) == 1:
            qa_flags.append("deprecated_symbol_used")
            return self._to_result(raw, prev_hits[0], "previous_symbol", 0.92, qa_flags, matched_alias=raw)
        if len(prev_hits) > 1:
            qa_flags.append("multiple_candidates")
            return self._ambiguous(raw, prev_hits, qa_flags)

        fuzzy = fuzzy_candidates(raw, list(self.by_symbol.keys()), threshold=0.9)
        if fuzzy:
            qa_flags.extend(["fuzzy_only", "low_confidence"])
            candidates = [
                NormalizationCandidate(
                    normalized_id=str(self.by_symbol[sym].get("hgnc_id", "")),
                    normalized_label=str(self.by_symbol[sym].get("symbol", "")),
                    source_authority="HGNC",
                    confidence=score,
                )
                for sym, score in fuzzy[:5]
                if sym in self.by_symbol
            ]
            return NormalizationResult(
                raw_input=raw,
                source_authority="HGNC",
                source_version=self.meta.source_version,
                match_type="fuzzy",
                confidence=0.45,
                candidates=candidates,
                qa_flags=qa_flags,
                metadata={"hgnc_file": self.hgnc_file},
            )

        return NormalizationResult(
            raw_input=raw,
            source_authority="HGNC",
            source_version=self.meta.source_version,
            match_type="unresolved",
            confidence=0.0,
            qa_flags=["unresolved"],
            metadata={"hgnc_file": self.hgnc_file},
        )

    def _to_result(
        self,
        raw: str,
        record: Dict[str, object],
        match_type: str,
        confidence: float,
        qa_flags: List[str],
        matched_alias: str = "",
    ) -> NormalizationResult:
        return NormalizationResult(
            raw_input=raw,
            normalized_id=str(record.get("hgnc_id", "")),
            normalized_label=str(record.get("symbol", "")),
            source_authority="HGNC",
            source_version=self.meta.source_version,
            match_type=match_type,  # type: ignore[arg-type]
            confidence=confidence,
            qa_flags=qa_flags,
            metadata={
                "approved_name": str(record.get("name", "")),
                "hgnc_id": str(record.get("hgnc_id", "")),
                "matched_alias": matched_alias,
                "hgnc_file": self.hgnc_file,
            },
        )

    def _ambiguous(self, raw: str, hits: List[Dict[str, object]], qa_flags: List[str]) -> NormalizationResult:
        candidates = [
            NormalizationCandidate(
                normalized_id=str(x.get("hgnc_id", "")),
                normalized_label=str(x.get("symbol", "")),
                source_authority="HGNC",
                confidence=0.5,
            )
            for x in hits[:8]
        ]
        qa_flags.extend(["authority_conflict", "low_confidence"])
        return NormalizationResult(
            raw_input=raw,
            source_authority="HGNC",
            source_version=self.meta.source_version,
            match_type="unresolved",
            confidence=0.2,
            candidates=candidates,
            qa_flags=sorted(set(qa_flags)),
            metadata={"hgnc_file": self.hgnc_file},
        )
