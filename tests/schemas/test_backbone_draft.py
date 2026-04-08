import pytest
from pydantic import ValidationError

from app.schemas.backbone_draft import DiseaseBackboneDraft


def test_backbone_draft_valid():
    d = DiseaseBackboneDraft(
        backbone_id="b1",
        builder_version="1",
        disease={"label": "PD", "ids": {}},
    )
    assert d.status == "draft"


def test_backbone_draft_missing_required():
    with pytest.raises(ValidationError):
        DiseaseBackboneDraft(builder_version="1", disease={"label": "PD", "ids": {}})


def test_backbone_draft_invalid_enum():
    with pytest.raises(ValidationError):
        DiseaseBackboneDraft(
            backbone_id="b1",
            builder_version="1",
            disease={"label": "PD", "ids": {}},
            status="final",
        )
