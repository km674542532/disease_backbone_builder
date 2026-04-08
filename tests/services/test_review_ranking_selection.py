from app.schemas.disease_descriptor import DiseaseDescriptor
from app.schemas.literature_record import LiteratureRecord
from app.services.review_ranker import ReviewRanker
from app.services.review_selector import ReviewSelector


def _rec(pmid: str, title: str, abstract: str, year: int, publication_types):
    return LiteratureRecord(
        literature_id=f"pmid:{pmid}",
        pmid=pmid,
        title=title,
        abstract=abstract,
        journal="Journal X",
        publication_year=year,
        publication_types=publication_types,
        authors=[],
        mesh_terms=[],
        retrieval_query_id="q1",
    )


def test_ranker_and_selector_bucket_targets():
    disease = DiseaseDescriptor(label="Parkinson disease", synonyms=["PD"])
    records = [
        _rec("1", "Parkinson disease review", "pathogenesis mechanism mitochondrial", 2024, ["Review"]),
        _rec("2", "Systematic review of PD", "mechanism pathway", 2023, ["Systematic Review"]),
        _rec("3", "Lysosomal mechanism in PD", "mitophagy proteostasis pathway", 2022, ["Review"]),
        _rec("4", "Broad neurodegenerative review", "neurodegenerative pathway", 2021, ["Review"]),
        _rec("5", "Another PD anchor", "Parkinson disease mechanism", 2025, ["Review"]),
    ]
    ranker = ReviewRanker(impact_factor_lookup=lambda _j: 3.0)
    ranked = ranker.rank(records, disease)
    selection, summary = ReviewSelector().select(ranked)

    assert ranked[0]["review_rank_score"] >= ranked[-1]["review_rank_score"]
    assert len(selection) == len(records)
    assert summary["selected_counts"]["anchor_review"] >= 2
    assert summary["selected_counts"]["systematic_review"] >= 1
