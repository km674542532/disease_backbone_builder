import json
from pathlib import Path

from app.pipelines.build_backbone import build
from app.utils.json_io import read_json


def test_build_backbone_supports_output_root_run_id_and_config(tmp_path: Path):
    input_path = tmp_path / "pd_sources.json"
    input_payload = [
        {
            "source_type": "ReviewArticle",
            "source_name": "Rev",
            "source_title": "PD Review",
            "sections": [{"section_label": "Mechanism", "text": "Mitophagy is impaired in PD."}],
        }
    ]
    input_path.write_text(json.dumps(input_payload), encoding="utf-8")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "aggregation_policy:\n"
        "  min_support_for_core_module: 1\n"
        "  min_support_for_core_hallmark: 1\n",
        encoding="utf-8",
    )

    output_root = tmp_path / "runs"
    run_id = "run_test_001"
    build(
        str(input_path),
        "Parkinson disease",
        llm_mode="mock",
        config_path=str(config_path),
        output_root=str(output_root),
        run_id=run_id,
    )

    run_root = output_root / run_id
    assert (run_root / "outputs" / "disease_backbone_draft.json").exists()
    assert (run_root / "outputs" / "validation_report.json").exists()
    effective = read_json(run_root / "config" / "effective_builder_config.json")
    assert effective["aggregation_policy"]["min_support_for_core_module"] == 1
