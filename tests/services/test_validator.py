from app.schemas.backbone_draft import DiseaseBackboneDraft
from app.services.validator import Validator


def test_validator_detects_invalid_chain():
    draft = DiseaseBackboneDraft.model_validate(
        {
            "backbone_id": "b1",
            "builder_version": "1",
            "disease": {"label": "PD", "ids": {}},
            "hallmarks": [],
            "modules": [],
            "module_relations": [],
            "canonical_chains": [
                {
                    "candidate_id": "c1",
                    "title": "short",
                    "module_label": "m",
                    "steps": [{"order": 1, "event_label": "a"}, {"order": 2, "event_label": "b"}],
                    "trigger_examples": [],
                    "supporting_source_packet_ids": ["sp_1"],
                    "candidate_confidence": 0.7,
                    "status": "candidate",
                }
            ],
            "key_genes": [],
            "source_summary": {"source_packet_count": 1, "source_type_counts": {"ReviewArticle": 1}},
            "build_quality": {"overall_confidence": 0.7, "items_needing_review": 0, "provisional_item_count": 0},
            "status": "draft",
        }
    )
    report = Validator().validate(draft)
    assert not report.checks["all_chains_have_multiple_steps"]
