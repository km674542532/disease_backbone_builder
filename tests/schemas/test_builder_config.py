import pytest
from pydantic import ValidationError

from app.schemas.builder_config import BuilderConfig


def test_builder_config_valid():
    obj = BuilderConfig(disease={"label": "Parkinson disease", "mondo_id": "MONDO:0005180"})
    assert obj.disease.label == "Parkinson disease"


def test_builder_config_missing_required():
    with pytest.raises(ValidationError):
        BuilderConfig()


def test_builder_config_invalid_enum():
    with pytest.raises(ValidationError):
        BuilderConfig(
            disease={"label": "X"},
            source_policy={"preferred_source_types": ["BadSource"]},
        )
