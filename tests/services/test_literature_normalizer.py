from app.schemas.literature_record import LiteratureRecord
from app.services.literature_normalizer import LiteratureNormalizer


def _record(**kwargs):
    base = {
        "literature_id": "pmid:1",
        "pmid": "1",
        "title": "Parkinson disease  review ",
        "journal": " J Neurol  ",
        "publication_year": 2022,
        "abstract": "mechanism pathway",
        "publication_types": ["review"],
        "authors": [],
        "mesh_terms": [],
        "retrieval_query_id": "q1",
    }
    base.update(kwargs)
    return LiteratureRecord(**base)


def test_normalizer_filters_and_dedups_by_priority():
    items = [
        _record(pmid="1", doi="10.1/a", literature_id="pmid:1"),
        _record(pmid="1", doi="10.1/b", literature_id="pmid:1b"),
        _record(pmid="2", doi="10.1/a", literature_id="pmid:2"),
        _record(pmid="3", title=" Parkinson disease review ", literature_id="pmid:3"),
        _record(pmid="4", language="fr", literature_id="pmid:4"),
        _record(pmid="5", abstract="", literature_id="pmid:5"),
    ]
    kept, stats = LiteratureNormalizer().normalize_and_dedup(items)
    assert len(kept) == 1
    assert stats["raw_count"] == 6
    assert stats["filtered_count"] == 5
    assert stats["dropped_reasons"]["duplicate_pmid"] >= 1
