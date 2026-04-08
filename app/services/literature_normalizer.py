"""Normalize and deduplicate PubMed literature records."""
from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.literature_record import LiteratureRecord
from app.utils.json_io import write_json, write_jsonl

logger = logging.getLogger(__name__)


class LiteratureNormalizer:
    def __init__(
        self,
        allowed_languages: Optional[List[str]] = None,
        min_publication_year: int = 1990,
        max_publication_year: Optional[int] = None,
    ) -> None:
        self.allowed_languages = {x.lower() for x in (allowed_languages or ["eng", "en"])}
        self.min_publication_year = min_publication_year
        self.max_publication_year = max_publication_year

    def _audit(self, status: str, **kwargs: object) -> None:
        kv = " ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info("audit stage=review_normalization_dedup status=%s %s", status, kv)

    @staticmethod
    def _normalize_title(title: str) -> str:
        compact = " ".join(title.split())
        compact = re.sub(r"[^a-z0-9 ]+", "", compact.lower())
        return re.sub(r"\s+", " ", compact).strip()

    @staticmethod
    def _normalize_journal(journal: str) -> str:
        return " ".join(journal.split())

    @staticmethod
    def _normalize_publication_types(publication_types: List[str]) -> List[str]:
        norm_map = {
            "systematic review": "Systematic Review",
            "meta-analysis": "Meta-Analysis",
            "review": "Review",
        }
        normalized = []
        for pt in publication_types:
            key = " ".join(pt.split()).lower()
            normalized.append(norm_map.get(key, " ".join(pt.split()).title()))
        return sorted(set(normalized))

    def normalize_and_dedup(self, records: List[LiteratureRecord]) -> Tuple[List[LiteratureRecord], Dict[str, object]]:
        self._audit("started", raw_count=len(records))
        dropped = Counter()
        seen_pmids: Set[str] = set()
        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        normalized: List[LiteratureRecord] = []

        for rec in records:
            payload = rec.model_dump()
            payload.update({
                "title": " ".join(rec.title.split()),
                "journal": self._normalize_journal(rec.journal),
                "publication_types": self._normalize_publication_types(rec.publication_types),
                "language": (rec.language or "").lower(),
            })
            clean = LiteratureRecord.model_validate(payload)
            title_key = self._normalize_title(clean.title)
            doi_key = clean.doi.lower() if clean.doi else ""

            if clean.language and clean.language not in self.allowed_languages:
                dropped["language_filtered"] += 1
                continue
            if clean.publication_year < self.min_publication_year:
                dropped["year_too_old"] += 1
                continue
            if self.max_publication_year is not None and clean.publication_year > self.max_publication_year:
                dropped["year_in_future"] += 1
                continue
            if not clean.abstract.strip():
                dropped["empty_abstract"] += 1
                continue

            if clean.pmid in seen_pmids:
                dropped["duplicate_pmid"] += 1
                continue
            if doi_key and doi_key in seen_dois:
                dropped["duplicate_doi"] += 1
                continue
            if title_key and title_key in seen_titles:
                dropped["duplicate_title"] += 1
                continue

            seen_pmids.add(clean.pmid)
            if doi_key:
                seen_dois.add(doi_key)
            if title_key:
                seen_titles.add(title_key)
            normalized.append(clean)

        write_jsonl("data/literature_records/literature_records_dedup.jsonl", [r.model_dump() for r in normalized])
        stats = {
            "raw_count": len(records),
            "dedup_count": len(normalized),
            "filtered_count": len(records) - len(normalized),
            "dropped_reasons": dict(dropped),
        }
        write_json(Path("data/literature_records") / "literature_normalization_stats.json", stats)
        self._audit("completed", dedup_count=stats["dedup_count"], filtered_count=stats["filtered_count"])
        return normalized, stats
