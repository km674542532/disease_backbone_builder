from app.schemas.extraction_result import ExtractionResult
from app.services.aggregator import Aggregator


def make_result(packet_id, hallmark_label):
    return ExtractionResult.model_validate(
        {
            "source_packet_id": packet_id,
            "disease": {"label": "PD", "mondo_id": "MONDO:1"},
            "hallmarks": [
                {
                    "candidate_id": f"h_{packet_id}",
                    "label": hallmark_label,
                    "normalized_label": "mitochondrial dysfunction",
                    "description": "x",
                    "evidence_scope": "disease_level",
                    "supporting_source_packet_ids": [packet_id],
                    "supporting_spans": [],
                    "candidate_confidence": 0.8,
                    "status": "candidate",
                }
            ],
            "modules": [],
            "module_relations": [],
            "causal_chains": [],
            "key_genes": [],
            "global_notes": [],
            "extraction_quality": {"llm_confidence": 0.8, "needs_manual_review": False, "warnings": []},
        }
    )


def test_aggregator_merges_duplicate_hallmarks():
    combined, records = Aggregator().aggregate([make_result("sp_1", "Mitochondrial dysfunction"), make_result("sp_2", "Mitochondrial impairment")])
    assert len(combined["hallmarks"]) == 1
    hallmark_records = [r for r in records if r.item_type == "hallmark"]
    assert hallmark_records[0].source_count == 2
