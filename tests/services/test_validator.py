import pytest
from pydantic import ValidationError

from app.schemas.backbone_draft import DiseaseBackboneDraft


def test_schema_rejects_invalid_chain_too_short():
    with pytest.raises(ValidationError):
        DiseaseBackboneDraft.model_validate(
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
