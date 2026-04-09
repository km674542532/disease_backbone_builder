"""PubMed E-utilities client for retrieval + normalization of review candidates."""
from __future__ import annotations

import json
import logging
import socket
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError

from app.schemas.literature_query_plan import LiteratureQueryPlan
from app.schemas.literature_record import LiteratureRecord
from app.utils.json_io import write_json, write_jsonl

logger = logging.getLogger(__name__)


class PubMedClient:
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        email: str,
        api_key: Optional[str] = None,
        timeout_seconds: int = 20,
        max_retries: int = 3,
        cache_raw: bool = True,
    ) -> None:
        self.email = email
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.cache_raw = cache_raw

    def _audit(self, stage: str, status: str, **kwargs: object) -> None:
        kv = " ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info("audit stage=%s status=%s %s", stage, status, kv)

    def _request(self, base_url: str, params: Dict[str, str]) -> str:
        if self.api_key:
            params["api_key"] = self.api_key
        params["email"] = self.email

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
                    return response.read().decode("utf-8")
            except HTTPError as exc:  # pragma: no cover - network exception branch
                last_error = exc
                if exc.code not in self.RETRYABLE_STATUS_CODES or attempt >= self.max_retries:
                    break
                time.sleep(0.5 * attempt)
            except (URLError, TimeoutError, socket.timeout) as exc:  # pragma: no cover - network exception branch
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.5 * attempt)
            except Exception as exc:  # pragma: no cover - network exception branch
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.5 * attempt)

        raise RuntimeError(f"PubMed request failed after retries: {url}") from last_error

    def esearch_pmids(self, query_plan: LiteratureQueryPlan) -> List[str]:
        stage = "review_retrieval.esearch"
        self._audit(stage, "started", query_id=query_plan.query_id)
        try:
            query = (
                f"({query_plan.query_string}) AND "
                f"{query_plan.date_range.start_year}:{query_plan.date_range.end_year}[dp]"
            )
            raw = self._request(
                self.ESEARCH_URL,
                {
                    "db": "pubmed",
                    "retmode": "json",
                    "retmax": str(query_plan.max_results),
                    "term": query,
                },
            )
            if self.cache_raw:
                write_json(Path("data/literature_records/raw") / f"esearch_{query_plan.query_id}.json", json.loads(raw))
            payload = json.loads(raw)
            pmids = payload.get("esearchresult", {}).get("idlist", [])
            self._audit(stage, "completed", query_id=query_plan.query_id, pmid_count=len(pmids))
            return pmids
        except Exception:
            self._audit(stage, "failed", query_id=query_plan.query_id)
            raise

    def efetch_records(self, pmids: List[str], query_plan: LiteratureQueryPlan) -> List[LiteratureRecord]:
        stage = "review_retrieval.efetch"
        self._audit(stage, "started", query_id=query_plan.query_id, pmid_count=len(pmids))
        if not pmids:
            self._audit(stage, "completed", query_id=query_plan.query_id, record_count=0)
            return []

        try:
            raw_xml = self._request(
                self.EFETCH_URL,
                {
                    "db": "pubmed",
                    "retmode": "xml",
                    "id": ",".join(pmids),
                },
            )
            if self.cache_raw:
                raw_dir = Path("data/literature_records/raw")
                raw_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / f"efetch_{query_plan.query_id}.xml").write_text(raw_xml, encoding="utf-8")

            records = self._parse_pubmed_xml(raw_xml, query_plan.query_id)
            write_jsonl("data/literature_records/literature_records.jsonl", [r.model_dump() for r in records])
            self._audit(stage, "completed", query_id=query_plan.query_id, record_count=len(records))
            return records
        except Exception:
            self._audit(stage, "failed", query_id=query_plan.query_id)
            raise

    def retrieve(self, query_plan: LiteratureQueryPlan) -> List[LiteratureRecord]:
        pmids = self.esearch_pmids(query_plan)
        return self.efetch_records(pmids, query_plan)

    @staticmethod
    def _parse_pubmed_xml(raw_xml: str, query_id: str) -> List[LiteratureRecord]:
        root = ET.fromstring(raw_xml)
        records: List[LiteratureRecord] = []
        for article in root.findall(".//PubmedArticle"):
            pmid = (article.findtext(".//PMID") or "").strip()
            title = " ".join((article.findtext(".//ArticleTitle") or "").split())
            abstract = "\n".join(
                t.strip() for t in article.findall(".//Abstract/AbstractText") if (t.text or "").strip()
            )
            journal = (article.findtext(".//Journal/Title") or "").strip()
            year_text = (article.findtext(".//PubDate/Year") or "0").strip()
            try:
                publication_year = int(year_text)
            except ValueError:
                publication_year = 0

            doi = None
            for aid in article.findall(".//ArticleId"):
                if aid.attrib.get("IdType") == "doi":
                    doi = (aid.text or "").strip() or None
                    break

            publication_types = [
                (pt.text or "").strip() for pt in article.findall(".//PublicationType") if (pt.text or "").strip()
            ]
            authors = []
            for author in article.findall(".//Author"):
                last = (author.findtext("LastName") or "").strip()
                initial = (author.findtext("Initials") or "").strip()
                if last:
                    authors.append(f"{last} {initial}".strip())
            mesh_terms = [
                (mh.findtext("DescriptorName") or "").strip()
                for mh in article.findall(".//MeshHeading")
                if (mh.findtext("DescriptorName") or "").strip()
            ]

            if not pmid:
                continue
            records.append(
                LiteratureRecord(
                    literature_id=f"pmid:{pmid}",
                    pmid=pmid,
                    doi=doi,
                    title=title,
                    abstract=abstract,
                    journal=journal,
                    publication_year=publication_year,
                    publication_types=publication_types,
                    authors=authors,
                    mesh_terms=mesh_terms,
                    retrieval_query_id=query_id,
                    pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )
        return records
