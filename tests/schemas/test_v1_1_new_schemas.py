import json

import pytest
from pydantic import ValidationError

from app.schemas.aggregation import BackboneAggregationRecord
from app.schemas.artifact_record import ArtifactRecord
from app.schemas.builder_config import BuilderConfig
from app.schemas.candidates import CausalChainCandidate
from app.schemas.disease_descriptor import DiseaseDescriptor
from app.schemas.literature_query_plan import LiteratureQueryPlan
from app.schemas.literature_record import LiteratureRecord
from app.schemas.review_selection_record import ReviewSelectionRecord
from app.schemas.rule_config import load_rule_config
from app.schemas.run_manifest import RunManifest
from app.schemas.source_document import SourceDocument
from app.schemas.source_manifest import SourceManifest


def test_construct_from_dict_to_dict_roundtrip():
    obj = DiseaseDescriptor.from_dict({"label": "Parkinson disease"})
    dumped = obj.to_dict()
    assert dumped["label"] == "Parkinson disease"


def test_invalid_enum_raises():
    with pytest.raises(ValidationError):
        ReviewSelectionRecord.from_dict(
            {
                "selection_id": "r1",
                "pmid": "1",
                "journal": "J",
                "publication_year": 2024,
                "review_bucket": "not_valid",
                "review_rank_score": 0.8,
                "mechanism_density_score": 0.7,
                "disease_specificity_score": 0.6,
                "decision": "selected",
            }
        )


def test_missing_required_field_raises():
    with pytest.raises(ValidationError):
        LiteratureRecord.from_dict({"literature_id": "x"})


def test_confidence_range_validation():
    with pytest.raises(ValidationError):
        BackboneAggregationRecord.from_dict(
            {
                "aggregation_id": "a1",
                "item_type": "module",
                "normalized_key": "mitophagy",
                "support_score": 1.2,
            }
        )


def test_chain_order_validation():
    with pytest.raises(ValidationError):
        CausalChainCandidate.from_dict(
            {
                "candidate_id": "c1",
                "title": "t",
                "module_label": "m",
                "steps": [{"order": 2, "event_label": "e2"}],
                "candidate_confidence": 0.6,
            }
        )


def test_rule_config_json_loads(tmp_path):
    payload = {
        "hallmark_rules": {"min_support_for_core_hallmark": 2, "generic_filter_terms": []},
        "module_rules": {
            "min_support_for_core_module": 2,
            "allowed_module_types": ["core_mechanism_module"],
            "generic_filter_terms": [],
        },
        "chain_rules": {"min_steps": 3, "min_chain_confidence": 0.7},
        "gene_rules": {"allowed_gene_roles": ["core_driver"], "require_module_link": True},
        "source_weights": {"GeneReviews": 1.0},
        "review_selection_rules": {
            "min_publication_year": 2018,
            "allowed_languages": ["eng"],
            "max_selected_reviews": 10,
            "max_selected_systematic_reviews": 5,
            "max_selected_specialized_reviews": 8,
        },
        "review_ranking_weights": {
            "review_type_weight": 0.3,
            "recency_weight": 0.2,
            "impact_factor_weight": 0.2,
            "mechanism_density_weight": 0.2,
            "disease_specificity_weight": 0.1,
        },
    }
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    cfg = load_rule_config(path)
    assert cfg.chain_rules.min_steps == 3


def test_manifest_schemas_constructable():
    src = SourceManifest.from_dict(
        {
            "run_id": "run_1",
            "disease_label": "Parkinson disease",
            "authoritative_source_document_ids": ["src_gr_pd_001"],
            "selected_review_source_document_ids": ["src_rev_pd_001"],
        }
    )
    run = RunManifest.from_dict(
        {
            "run_id": "run_1",
            "disease": "Parkinson disease",
            "builder_version": "1.1.0",
            "stages": [],
            "output_paths": {"draft": "data/outputs/pd_backbone_draft_v1_1.json"},
        }
    )
    artifact = ArtifactRecord.from_dict(
        {
            "artifact_type": "source_packets",
            "path": "data/source_packets/source_packets.jsonl",
            "created_at": "2026-04-08T00:00:00Z",
            "count": 12,
            "status": "completed",
        }
    )
    source_doc = SourceDocument.from_dict(
        {
            "source_document_id": "src_1",
            "disease_label": "Parkinson disease",
            "source_type": "GeneReviews",
            "source_name": "GeneReviews",
            "source_title": "PD",
            "priority_tier": "anchor_review",
        }
    )

    assert src.run_id == run.run_id
    assert artifact.count == 12
    assert source_doc.source_type == "GeneReviews"


def test_builder_config_new_fields_present():
    cfg = BuilderConfig.from_dict({"disease": {"label": "Parkinson disease"}})
    assert cfg.literature_policy.max_pubmed_candidates == 200
    assert cfg.ranking_policy.impact_factor_weight == 0.2


def test_literature_query_plan_required_fields():
    with pytest.raises(ValidationError):
        LiteratureQueryPlan.from_dict({"query_id": "q1"})
