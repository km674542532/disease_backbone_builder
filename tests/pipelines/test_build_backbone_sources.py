import json
from pathlib import Path

import pytest

from app.pipelines import build_backbone


@pytest.fixture
def local_input_file(tmp_path: Path) -> Path:
    input_path = tmp_path / "local_sources.json"
    payload = [
        {
            "source_type": "ReviewArticle",
            "source_name": "LocalReview",
            "source_title": "Local PD Review",
            "sections": [{"section_label": "Mechanism", "text": "mitophagy defect in PD"}],
        }
    ]
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    return input_path


def _write_pubmed_jsonl(path: Path) -> None:
    row = {
        "source_type": "ReviewArticle",
        "record_id": "pmid:1",
        "disease": "Parkinson disease",
        "pmid": "1",
        "title": "PubMed PD review",
        "abstract": "pathogenesis mechanism",
        "journal": "Journal X",
        "publication_date": "2024-01-01",
        "article_types": ["Review"],
        "authors": ["Doe J"],
        "mesh_terms": ["Parkinson Disease"],
        "query": "pd review",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
        "source_name": "Journal X",
        "source_title": "PubMed PD review",
        "sections": [{"section_label": "abstract", "text": "pathogenesis mechanism"}],
        "metadata": {"is_review_like": True},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_build_backbone_local_only(local_input_file: Path):
    build_backbone.build(str(local_input_file), "Parkinson disease")
    assert Path("data/outputs/disease_backbone_draft.json").exists()


def test_build_backbone_pubmed_only_with_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pubmed_cache = tmp_path / "pd_pubmed.jsonl"
    _write_pubmed_jsonl(pubmed_cache)

    monkeypatch.setattr(build_backbone, "run_pubmed_retrieval", lambda **_kwargs: str(pubmed_cache))

    build_backbone.build(
        None,
        "Parkinson disease",
        use_pubmed=True,
        pubmed_email="test@example.com",
    )

    assert Path("data/outputs/validation_report.json").exists()


def test_build_backbone_local_plus_pubmed(local_input_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pubmed_cache = tmp_path / "pd_pubmed.jsonl"
    _write_pubmed_jsonl(pubmed_cache)

    monkeypatch.setattr(build_backbone, "run_pubmed_retrieval", lambda **_kwargs: str(pubmed_cache))

    build_backbone.build(
        str(local_input_file),
        "Parkinson disease",
        use_pubmed=True,
        pubmed_email="test@example.com",
    )

    assert Path("data/source_packets/source_packets.jsonl").exists()


def test_pubmed_failure_fallback_to_local(local_input_file: Path, monkeypatch: pytest.MonkeyPatch):
    def _raise(**_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(build_backbone, "run_pubmed_retrieval", _raise)

    build_backbone.build(
        str(local_input_file),
        "Parkinson disease",
        use_pubmed=True,
        pubmed_email="test@example.com",
    )

    assert Path("data/outputs/review_bundle/backbone_summary.json").exists()
