"""LLM constrained extractor from SourcePacket to ExtractionResult."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from app.schemas.extraction_result import ExtractionResult
from app.schemas.source_packet import SourcePacket
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Structured JSON extractor with schema validation and error logging."""

    def __init__(self, llm_client: LLMClient, prompt_path: str = "app/prompts/packet_extraction.txt"):
        self.llm_client = llm_client
        self.prompt_template = Path(prompt_path).read_text(encoding="utf-8")

    def extract(self, packet: SourcePacket, disease_ids: Dict[str, Any], seed_genes: list[str]) -> ExtractionResult:
        prompt = self._render_prompt(packet, disease_ids, seed_genes)
        try:
            response_obj = self.llm_client.generate_json(prompt)
        except Exception as exc:
            logger.exception(
                "llm_call_failed source_packet_id=%s prompt=packet_extraction error_type=%s",
                packet.source_packet_id,
                type(exc).__name__,
            )
            raise

        try:
            payload = {
                "source_packet_id": packet.source_packet_id,
                "disease": {"label": packet.disease_label, "mondo_id": disease_ids.get("mondo")},
                **response_obj,
            }
            return ExtractionResult.model_validate(payload)
        except (ValidationError, ValueError, TypeError) as exc:
            raw = json.dumps(response_obj, ensure_ascii=False)[:500]
            logger.exception(
                "schema_validation_failed source_packet_id=%s prompt=packet_extraction error_type=%s raw_response=%s",
                packet.source_packet_id,
                type(exc).__name__,
                raw,
            )
            raise

    def _render_prompt(self, packet: SourcePacket, disease_ids: Dict[str, Any], seed_genes: list[str]) -> str:
        prompt = self.prompt_template
        prompt = prompt.replace("{{ disease_name }}", packet.disease_label)
        prompt = prompt.replace("{{ disease_ids_json }}", json.dumps(disease_ids, ensure_ascii=False))
        prompt = prompt.replace("{{ seed_genes_json }}", json.dumps(seed_genes, ensure_ascii=False))
        prompt = prompt.replace(
            "{{ source_packet_metadata_json }}",
            json.dumps({
                "source_packet_id": packet.source_packet_id,
                "source_type": packet.source_type,
                "source_title": packet.source_title,
                "section_label": packet.section_label,
                "source_locator": packet.source_locator.model_dump(),
                "metadata": packet.metadata,
            }, ensure_ascii=False),
        )
        prompt = prompt.replace("{{ source_text }}", packet.text_block)
        return prompt
