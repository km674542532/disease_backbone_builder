import json
from pathlib import Path

from app.pipelines.build_backbone import build


def test_pipeline_smoke(tmp_path: Path):
    input_path = tmp_path / "pd_sources.json"
    input_payload = [
        {
            "source_type": "ReviewArticle",
            "source_name": "Rev",
            "source_title": "PD Review",
            "sections": [
                {"section_label": "Mechanism", "text": "Mitophagy is impaired in PD."}
            ],
        }
    ]
    input_path.write_text(json.dumps(input_payload), encoding="utf-8")

    build(str(input_path), "Parkinson disease")

    assert Path("data/outputs/disease_backbone_draft.json").exists()
    assert Path("data/outputs/validation_report.json").exists()
    assert Path("data/outputs/review_bundle/backbone_summary.json").exists()
