import pytest
from pydantic import ValidationError

from app.schemas.disease_descriptor import DiseaseDescriptor


def test_disease_descriptor_valid():
    d = DiseaseDescriptor(label="Parkinson disease")
    assert d.label


def test_disease_descriptor_missing_required():
    with pytest.raises(ValidationError):
        DiseaseDescriptor()


def test_disease_descriptor_extra_field_error():
    with pytest.raises(ValidationError):
        DiseaseDescriptor(label="X", unknown="y")
