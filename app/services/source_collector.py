"""Collect sources from local JSON/JSONL or structured text files."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from app.utils.json_io import read_jsonl

logger = logging.getLogger(__name__)


class SourceCollector:
    """MVP source collector for local disk inputs only."""

    def collect(self, input_path: str) -> List[Dict[str, Any]]:
        logger.info("stage_start source_collect input=%s", input_path)
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(input_path)
        if path.suffix == ".jsonl":
            rows = read_jsonl(path)
        elif path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict) and "sources" in data:
                rows = data["sources"]
            else:
                rows = [data]
        else:
            text = path.read_text(encoding="utf-8")
            rows = [
                {
                    "source_type": "Other",
                    "source_name": path.stem,
                    "source_title": path.name,
                    "sections": [{"section_label": "raw_text", "text": text}],
                }
            ]
        logger.info("stage_end source_collect count=%d", len(rows))
        return rows
