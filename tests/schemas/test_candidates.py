import pytest
from pydantic import ValidationError

from app.schemas.candidates import ModuleRelation


def test_candidates_valid():
    m = ModuleRelation(
        candidate_id="r1",
        subject_module="a",
        predicate="upstream_of",
        object_module="b",
        description="d",
        candidate_confidence=0.8,
    )
    assert m.predicate == "upstream_of"


def test_candidates_missing_required():
    with pytest.raises(ValidationError):
        ModuleRelation(candidate_id="r1")


def test_candidates_invalid_enum():
    with pytest.raises(ValidationError):
        ModuleRelation(
            candidate_id="r1",
            subject_module="a",
            predicate="wrong",
            object_module="b",
            description="d",
            candidate_confidence=0.8,
        )
