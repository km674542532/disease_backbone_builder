from app.services.extraction_adapter import ExtractionAdapter


def test_extraction_adapter_maps_aliases_and_defaults():
    adapter = ExtractionAdapter()
    raw = {
        "modules": [{"module_id": "m1", "module_label": "Mitophagy", "confidence": 1.2}],
        "relations": [{"relation_id": "r1", "subject": "Mitophagy", "object": "Inflammation", "predicate": "unknown"}],
        "chains": [{"chain_id": "c1", "module": "Mitophagy", "steps": [{"event": "A"}], "confidence": 0.7}],
        "genes": [{"gene_id": "g1", "gene_symbol": "LRRK2", "gene_role": "unknown"}],
        "extraction_quality": {"confidence": 0.8},
    }

    adapted = adapter.adapt(raw, "sp_0001")

    assert adapted["modules"][0]["candidate_id"] == "m1"
    assert adapted["modules"][0]["candidate_confidence"] == 1.0
    assert adapted["modules"][0]["supporting_source_packet_ids"] == ["sp_0001"]
    assert adapted["module_relations"][0]["predicate"] == "linked_to"
    assert adapted["causal_chains"][0]["steps"][0]["order"] == 1
    assert adapted["key_genes"][0]["gene_role"] == "uncertain"
    assert adapted["extraction_quality"]["llm_confidence"] == 0.8


def test_extraction_adapter_tolerates_non_object_quality_payload():
    adapter = ExtractionAdapter()
    adapted = adapter.adapt({"extraction_quality": ["oops"]}, "sp_0002")

    assert adapted["extraction_quality"]["llm_confidence"] == 0.0
    assert adapted["extraction_quality"]["parse_status"] == "ok"
