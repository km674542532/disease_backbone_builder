import pytest
from pydantic import ValidationError

from app.schemas.source_packet import SourcePacket


def test_source_packet_valid():
    p = SourcePacket(
        source_packet_id="sp_1",
        disease_label="PD",
        source_type="ReviewArticle",
        source_name="R",
        source_title="T",
        section_label="S",
        text_block="abc",
    )
    assert p.source_type == "ReviewArticle"


def test_source_packet_missing_required():
    with pytest.raises(ValidationError):
        SourcePacket(source_packet_id="sp_1")


def test_source_packet_invalid_enum():
    with pytest.raises(ValidationError):
        SourcePacket(
            source_packet_id="sp_1",
            disease_label="PD",
            source_type="Wiki",
            source_name="R",
            source_title="T",
            section_label="S",
            text_block="abc",
        )
