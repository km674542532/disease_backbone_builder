import pytest
from pydantic import ValidationError

from app.schemas.aggregation import BackboneAggregationRecord


def test_aggregation_valid():
    r = BackboneAggregationRecord(aggregation_id="a1", item_type="module", normalized_key="x")
    assert r.item_type == "module"


def test_aggregation_missing_required():
    with pytest.raises(ValidationError):
        BackboneAggregationRecord(item_type="module", normalized_key="x")


def test_aggregation_invalid_enum():
    with pytest.raises(ValidationError):
        BackboneAggregationRecord(aggregation_id="a1", item_type="x", normalized_key="x")
