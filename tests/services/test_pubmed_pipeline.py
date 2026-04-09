import json
from pathlib import Path

from app.schemas.literature_query_plan import LiteratureQueryPlan, QueryDateRange
from app.schemas.literature_record import LiteratureRecord
from app.services.literature.pubmed_pipeline import run_pubmed_retrieval


class _FakePubMedClient:
    def __init__(self, email, api_key=None):
        self.email = email
        self.api_key = api_key

    def esearch_pmids(self, _query_plan):
        return ["123"]

    def efetch_records(self, _pmids, query_plan):
        return [
            LiteratureRecord(
                literature_id="pmid:123",
                pmid="123",
                title="Parkinson disease review",
                abstract="mechanism",
                journal="J Neurol",
                publication_year=2024,
                publication_types=["Review"],
                authors=["Doe J"],
                mesh_terms=["Parkinson Disease"],
                retrieval_query_id=query_plan.query_id,
                pubmed_url="https://pubmed.ncbi.nlm.nih.gov/123/",
            )
        ]


def test_pubmed_cache_hit(tmp_path: Path):
    cache = tmp_path / "literature_records"
    cache.mkdir(parents=True, exist_ok=True)
    output = cache / "parkinson_disease_pubmed.jsonl"
    output.write_text("{}\n", encoding="utf-8")

    returned = run_pubmed_retrieval(
        disease="Parkinson disease",
        email="test@example.com",
        cache_dir=str(cache),
        refresh=False,
    )

    assert returned == str(output)


def test_pubmed_retrieval_writes_standardized_rows(tmp_path: Path, monkeypatch):
    cache = tmp_path / "literature_records"

    monkeypatch.setattr("app.services.literature.pubmed_pipeline.PubMedClient", _FakePubMedClient)
    monkeypatch.setattr(
        "app.services.literature.pubmed_pipeline._build_query_plan",
        lambda disease, max_reviews, days_back, override_query: LiteratureQueryPlan(
            query_id="q1",
            disease_label=disease,
            query_family="review_discovery",
            query_string="pd review",
            date_range=QueryDateRange(start_year=2020, end_year=2026),
            language_filter=["eng"],
            max_results=max_reviews,
            priority=1,
        ),
    )

    path = run_pubmed_retrieval(
        disease="Parkinson disease",
        email="test@example.com",
        cache_dir=str(cache),
        refresh=True,
    )

    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    row = rows[0]
    required = {
        "source_type",
        "record_id",
        "disease",
        "pmid",
        "title",
        "abstract",
        "journal",
        "publication_date",
        "article_types",
        "authors",
        "mesh_terms",
        "query",
        "retrieved_at",
    }
    assert required.issubset(row.keys())
