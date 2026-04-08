import pytest
from pydantic import ValidationError

from app.schemas.validation_report import ValidationReport


def test_validation_report_valid():
    v = ValidationReport(backbone_id="b1", validation_passed=True)
    assert v.validation_passed


def test_validation_report_missing_required():
    with pytest.raises(ValidationError):
        ValidationReport(backbone_id="b1")


def test_validation_report_extra_field_error():
    with pytest.raises(ValidationError):
        ValidationReport(backbone_id="b1", validation_passed=True, x=1)
