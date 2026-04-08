from app.schemas.source_packet import SourcePacket
from app.services.llm_client import MockLLMClient
from app.services.llm_extractor import LLMExtractor


def test_llm_extractor_returns_extraction_result():
    response = {
        "hallmarks": [],
        "modules": [],
        "module_relations": [],
        "causal_chains": [],
        "key_genes": [],
        "global_notes": ["ok"],
        "extraction_quality": {"llm_confidence": 0.91, "needs_manual_review": False, "warnings": []},
    }
    ext = LLMExtractor(MockLLMClient(response))
    packet = SourcePacket(
        source_packet_id="sp_1",
        disease_label="PD",
        source_type="ReviewArticle",
        source_name="R",
        source_title="T",
        section_label="S",
        text_block="text",
    )
    result = ext.extract(packet, {"mondo": "MONDO:1"}, [])
    assert result.extraction_quality.llm_confidence == 0.91
