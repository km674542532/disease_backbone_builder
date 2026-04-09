"""Orchestrate PubMed retrieval and cache to local JSONL for SourceCollector."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.schemas.disease_descriptor import DiseaseDescriptor
from app.schemas.literature_query_plan import LiteratureQueryPlan, QueryDateRange
from app.services.pubmed_client import PubMedClient
from app.services.review_query_builder import ReviewQueryBuilder
from app.utils.json_io import write_json, write_jsonl

logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    return "_".join(value.lower().strip().split())


def _format_publication_date(year: int) -> str:
    if year > 0:
        return f"{year}-01-01"
    return ""


def _to_source_row(record: Dict[str, object], disease: str, query: str, retrieved_at: str) -> Dict[str, object]:
    abstract = str(record.get("abstract") or "")
    section_text = abstract or str(record.get("title") or "")
    pmid = str(record.get("pmid") or "")
    return {
        "source_type": "ReviewArticle",
        "record_id": str(record.get("literature_id") or f"pmid:{pmid}"),
        "disease": disease,
        "pmid": pmid,
        "title": str(record.get("title") or ""),
        "abstract": abstract,
        "journal": str(record.get("journal") or ""),
        "publication_date": _format_publication_date(int(record.get("publication_year") or 0)),
        "article_types": list(record.get("publication_types") or []),
        "authors": list(record.get("authors") or []),
        "mesh_terms": list(record.get("mesh_terms") or []),
        "query": query,
        "retrieved_at": retrieved_at,
        "source_name": str(record.get("journal") or "PubMed"),
        "source_title": str(record.get("title") or pmid or "PubMed Record"),
        "sections": [{"section_label": "abstract", "text": section_text}],
        "metadata": {
            "doi": record.get("doi"),
            "pubmed_url": record.get("pubmed_url"),
            "retrieval_query_id": record.get("retrieval_query_id"),
            "is_review_like": True,
            "is_authoritative_summary": False,
        },
    }


def _build_query_plan(
    disease: str,
    max_reviews: int,
    days_back: Optional[int],
    override_query: Optional[str],
) -> LiteratureQueryPlan:
    now = datetime.now(timezone.utc)
    if override_query:
        years = max(1, int((days_back or 3650) / 365))
        return LiteratureQueryPlan(
            query_id=f"{_slugify(disease)}_override",
            disease_label=disease,
            query_family="override",
            query_string=override_query,
            date_range=QueryDateRange(start_year=now.year - years, end_year=now.year),
            language_filter=["eng"],
            max_results=max_reviews,
            priority=1,
            notes="User overridden PubMed query.",
        )

    descriptor = DiseaseDescriptor(label=disease)
    plans = ReviewQueryBuilder(default_max_results=max_reviews).build(descriptor)
    selected = plans[0]
    if days_back:
        lookback_years = max(1, int(days_back / 365))
        selected.date_range = QueryDateRange(start_year=now.year - lookback_years, end_year=now.year)
    return selected


def run_pubmed_retrieval(
    *,
    disease: str,
    max_reviews: int = 50,
    email: Optional[str] = None,
    api_key: Optional[str] = None,
    cache_dir: str = "data/literature_records",
    days_back: Optional[int] = None,
    override_query: Optional[str] = None,
    refresh: bool = False,
) -> Optional[str]:
    logger.info("pubmed_retrieval_started disease=%s refresh=%s", disease, refresh)
    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)

    slug = _slugify(disease)
    output_jsonl = cache_root / f"{slug}_pubmed.jsonl"
    output_meta = cache_root / f"{slug}_pubmed.meta.json"

    if not refresh and output_jsonl.exists():
        logger.info("pubmed_cache_hit disease=%s path=%s", disease, output_jsonl)
        return str(output_jsonl)

    if not email:
        raise ValueError("pubmed_email is required when refreshing PubMed retrieval.")

    query_plan = _build_query_plan(disease, max_reviews, days_back, override_query)
    logger.info("pubmed_query_built disease=%s query_id=%s", disease, query_plan.query_id)

    client = PubMedClient(email=email, api_key=api_key)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    try:
        pmids = client.esearch_pmids(query_plan)
        logger.info("pubmed_esearch_completed disease=%s query_id=%s pmid_count=%d", disease, query_plan.query_id, len(pmids))
        records = client.efetch_records(pmids, query_plan)
        logger.info("pubmed_efetch_completed disease=%s query_id=%s record_count=%d", disease, query_plan.query_id, len(records))
    except Exception as exc:
        raise RuntimeError(
            f"PubMed retrieval failed for disease={disease}, query_id={query_plan.query_id}: {exc}"
        ) from exc

    rows = [_to_source_row(r.model_dump(), disease, query_plan.query_string, retrieved_at) for r in records]
    write_jsonl(output_jsonl, rows)
    write_json(
        output_meta,
        {
            "disease": disease,
            "query_id": query_plan.query_id,
            "query": query_plan.query_string,
            "retrieved_at": retrieved_at,
            "record_count": len(rows),
            "cache_file": str(output_jsonl),
            "days_back": days_back,
            "override_query": override_query,
            "max_reviews": max_reviews,
        },
    )

    return str(output_jsonl)
