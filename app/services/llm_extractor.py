"""LLM constrained extractor from SourcePacket to ExtractionResult."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from app.schemas.extraction_result import ExtractionResult
from app.schemas.source_packet import SourcePacket
from app.services.extraction_adapter import ExtractionAdapter
from app.services.llm_client import LLMClient
from app.utils.json_io import write_jsonl

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Qwen-only schema-constrained extractor with per-packet audit logs."""

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_path: str = "app/prompts/packet_extraction.txt",
        provider: str = "qwen",
    ):
        if provider.lower() != "qwen":
            raise ValueError("Only qwen provider is supported for constrained extraction")
        self.llm_client = llm_client
        self.provider = provider.lower()
        self.prompt_template = Path(prompt_path).read_text(encoding="utf-8")
        self.adapter = ExtractionAdapter()

    def extract(self, packet: SourcePacket, disease_ids: Dict[str, Any], seed_genes: list[str]) -> ExtractionResult:
        """Extract one packet as constrained JSON and validate against ExtractionResult schema."""
        result, _raw_response, _latency_ms = self._extract_with_raw(packet, disease_ids, seed_genes)
        return result

    def _extract_with_raw(
        self,
        packet: SourcePacket,
        disease_ids: Dict[str, Any],
        seed_genes: list[str],
    ) -> Tuple[ExtractionResult, Dict[str, Any], float]:
        started_at = time.perf_counter()
        logger.info("stage_started stage=extraction provider=%s source_packet_id=%s", self.provider, packet.source_packet_id)
        prompt = self._render_prompt(packet, disease_ids, seed_genes)
        response_obj: Dict[str, Any] = {}
        parse_status = "ok"
        schema_validation_status = "ok"
        try:
            response_obj = self.llm_client.generate_json(prompt)
            if not isinstance(response_obj, dict):
                raise TypeError("Constrained extraction must return a JSON object")
        except Exception as exc:
            parse_status = "failed"
            schema_validation_status = "skipped"
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "stage_failed stage=extraction source_packet_id=%s latency_ms=%.2f parse_status=%s schema_validation_status=%s error_type=%s",
                packet.source_packet_id,
                latency_ms,
                parse_status,
                schema_validation_status,
                type(exc).__name__,
            )
            return (
                self._failed_result(packet, disease_ids, parse_status, schema_validation_status, str(exc)),
                {"error": str(exc)},
                latency_ms,
            )

        try:
            adapted_response = self.adapter.adapt(response_obj, packet.source_packet_id)
            payload = {
                "source_packet_id": packet.source_packet_id,
                "disease": {"label": packet.disease_label, "mondo_id": disease_ids.get("mondo")},
                **adapted_response,
            }
            result = ExtractionResult.model_validate(payload)
            result.extraction_quality.parse_status = parse_status
            result.extraction_quality.schema_validation_status = schema_validation_status
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "stage_completed stage=extraction source_packet_id=%s latency_ms=%.2f parse_status=%s schema_validation_status=%s",
                packet.source_packet_id,
                latency_ms,
                parse_status,
                schema_validation_status,
            )
            return result, response_obj, latency_ms
        except (ValidationError, ValueError, TypeError) as exc:
            parse_status = "ok"
            schema_validation_status = "failed"
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "stage_failed stage=extraction source_packet_id=%s latency_ms=%.2f parse_status=%s schema_validation_status=%s error_type=%s",
                packet.source_packet_id,
                latency_ms,
                parse_status,
                schema_validation_status,
                type(exc).__name__,
            )
            return (
                self._failed_result(packet, disease_ids, parse_status, schema_validation_status, str(exc)),
                response_obj,
                latency_ms,
            )

    def extract_packets(
        self,
        packets: List[SourcePacket],
        disease_ids: Dict[str, Any],
        seed_genes: list[str],
        extraction_results_path: str | Path = "data/extraction_results/extraction_results.jsonl",
        raw_llm_responses_path: str | Path = "data/extraction_results/raw_llm_responses.jsonl",
    ) -> Tuple[List[ExtractionResult], List[str]]:
        """Batch extraction with persistence and failed packet tracking."""
        results: List[ExtractionResult] = []
        failed_packet_ids: List[str] = []
        raw_rows: List[Dict[str, Any]] = []

        for packet in packets:
            result, raw_response, latency_ms = self._extract_with_raw(packet, disease_ids, seed_genes)

            raw_rows.append(
                {
                    "source_packet_id": packet.source_packet_id,
                    "provider": self.provider,
                    "latency_ms": latency_ms,
                    "parse_status": result.extraction_quality.parse_status,
                    "schema_validation_status": result.extraction_quality.schema_validation_status,
                    "raw_response": raw_response,
                }
            )
            if result.extraction_quality.schema_validation_status == "failed" or result.extraction_quality.parse_status == "failed":
                failed_packet_ids.append(packet.source_packet_id)
            results.append(result)

        write_jsonl(extraction_results_path, [r.model_dump() for r in results])
        write_jsonl(raw_llm_responses_path, raw_rows)
        return results, failed_packet_ids

    def _failed_result(
        self,
        packet: SourcePacket,
        disease_ids: Dict[str, Any],
        parse_status: str,
        schema_validation_status: str,
        error_message: str,
    ) -> ExtractionResult:
        return ExtractionResult.model_validate(
            {
                "source_packet_id": packet.source_packet_id,
                "disease": {"label": packet.disease_label, "mondo_id": disease_ids.get("mondo")},
                "hallmarks": [],
                "modules": [],
                "module_relations": [],
                "causal_chains": [],
                "key_genes": [],
                "global_notes": [f"extraction_failed: {error_message[:200]}"],
                "extraction_quality": {
                    "llm_confidence": 0.0,
                    "needs_manual_review": True,
                    "warnings": ["packet extraction failed; emitted empty candidates"],
                    "parse_status": parse_status,
                    "schema_validation_status": schema_validation_status,
                },
            }
        )

    def _render_prompt(self, packet: SourcePacket, disease_ids: Dict[str, Any], seed_genes: list[str]) -> str:
        prompt = self.prompt_template
        prompt = prompt.replace("{{ disease_name }}", packet.disease_label)
        prompt = prompt.replace("{{ disease_ids_json }}", json.dumps(disease_ids, ensure_ascii=False))
        prompt = prompt.replace("{{ seed_genes_json }}", json.dumps(seed_genes, ensure_ascii=False))
        prompt = prompt.replace(
            "{{ source_packet_metadata_json }}",
            json.dumps(
                {
                    "source_packet_id": packet.source_packet_id,
                    "source_document_id": packet.source_document_id,
                    "source_type": packet.source_type,
                    "source_title": packet.source_title,
                    "section_label": packet.section_label,
                    "selection_metadata": packet.selection_metadata,
                    "metadata": packet.metadata,
                },
                ensure_ascii=False,
            ),
        )
        prompt = prompt.replace("{{ source_text }}", packet.text_block)
        return prompt
