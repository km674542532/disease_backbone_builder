import pytest
from pydantic import ValidationError

from app.schemas.extraction_result import ExtractionResult


def _payload():
    return {
        "source_packet_id": "sp_1",
        "disease": {"label": "PD", "mondo_id": "MONDO:1"},
        "hallmarks": [],
        "modules": [],
        "module_relations": [],
        "causal_chains": [],
        "key_genes": [],
        "global_notes": [],
        "extraction_quality": {"llm_confidence": 0.9, "needs_manual_review": False, "warnings": []},
    }


def test_extraction_result_valid():
    assert ExtractionResult.model_validate(_payload()).source_packet_id == "sp_1"


def test_extraction_result_missing_required():
    bad = _payload()
    bad.pop("source_packet_id")
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate(bad)


def test_extraction_result_invalid_enum():
    bad = _payload()
    bad["modules"] = [{
        "candidate_id": "m1",
        "label": "x",
        "normalized_label": "x",
        "description": "x",
        "module_type": "wrong",
        "hallmark_links": [],
        "key_genes": [],
        "process_terms": [],
        "supporting_source_packet_ids": [],
        "candidate_confidence": 0.7,
        "status": "candidate",
    }]
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate(bad)
