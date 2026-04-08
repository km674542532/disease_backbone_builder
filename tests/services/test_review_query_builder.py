from app.schemas.disease_descriptor import DiseaseDescriptor, DiseaseIds
from app.services.review_query_builder import ReviewQueryBuilder


def test_pd_query_builder_generates_three_nonempty_queries():
    disease = DiseaseDescriptor(
        label="Parkinson disease",
        synonyms=["Parkinson's disease", "PD"],
        ids=DiseaseIds(mesh="Parkinson Disease"),
    )
    plans = ReviewQueryBuilder().build(disease)

    assert len(plans) >= 3
    assert {p.query_family for p in plans} >= {
        "review_discovery",
        "systematic_review_discovery",
        "mechanism_review_discovery",
    }
    assert all(p.query_string.strip() for p in plans)
