from app.schemas.literature_record import LiteratureRecord
from app.schemas.review_selection_record import ReviewSelectionRecord
from app.schemas.source_document import SourceDocument
from app.services.source_document_assembler import SourceDocumentAssembler


def test_source_document_assembler_merges_authoritative_and_selected_reviews():
    authoritative = [
        SourceDocument(
            source_document_id="src_auth_1",
            disease_label="Parkinson disease",
            source_type="GeneReviews",
            source_name="GeneReviews",
            source_title="PD GeneReviews",
            priority_tier="authoritative",
        )
    ]
    sel = [
        ReviewSelectionRecord(
            selection_id="sel_1",
            pmid="123",
            journal="Journal A",
            publication_year=2023,
            review_bucket="anchor_review",
            review_rank_score=0.8,
            mechanism_density_score=0.7,
            disease_specificity_score=0.9,
            decision="selected",
        )
    ]
    literature = {
        "123": LiteratureRecord(
            literature_id="pmid:123",
            pmid="123",
            title="PD review",
            abstract="mechanism",
            journal="Journal A",
            publication_year=2023,
            publication_types=["Review"],
            authors=[],
            mesh_terms=[],
            retrieval_query_id="q1",
        )
    }

    docs = SourceDocumentAssembler().assemble("Parkinson disease", authoritative, sel, literature)
    assert len(docs) == 2
    assert any(d.source_type == "ReviewArticle" for d in docs)
