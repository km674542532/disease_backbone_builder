"""Adapter that normalizes LLM JSON output before strict schema validation."""
from __future__ import annotations

from typing import Any, Dict, List


_ALLOWED_STATUSES = {"candidate", "provisional"}
_ALLOWED_MODULE_TYPES = {
    "core_mechanism_module",
    "supporting_module",
    "phenotype_convergence_module",
    "peripheral_module",
}
_ALLOWED_PREDICATES = {
    "upstream_of",
    "downstream_of",
    "interacts_with",
    "converges_on",
    "amplifies",
    "impairs",
    "supports",
    "linked_to",
}
_ALLOWED_GENE_ROLES = {
    "core_driver",
    "major_associated_gene",
    "module_specific_gene",
    "supporting_gene",
    "uncertain",
}


class ExtractionAdapter:
    """Normalize common LLM drift patterns into ExtractionResult-compatible payload."""

    def adapt(self, raw: Dict[str, Any], source_packet_id: str) -> Dict[str, Any]:
        payload = dict(raw or {})
        payload["hallmarks"] = self._adapt_hallmarks(payload.get("hallmarks", []), source_packet_id)
        payload["modules"] = self._adapt_modules(payload.get("modules", []), source_packet_id)
        payload["module_relations"] = self._adapt_module_relations(
            payload.get("module_relations", payload.get("relations", [])),
            source_packet_id,
        )
        payload["causal_chains"] = self._adapt_causal_chains(
            payload.get("causal_chains", payload.get("chains", [])),
            source_packet_id,
        )
        payload["key_genes"] = self._adapt_key_genes(payload.get("key_genes", payload.get("genes", [])), source_packet_id)
        payload["global_notes"] = self._as_str_list(payload.get("global_notes", []))
        payload["extraction_quality"] = self._adapt_extraction_quality(payload.get("extraction_quality", {}))
        return payload

    def _adapt_hallmarks(self, items: Any, source_packet_id: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for i, item in enumerate(items if isinstance(items, list) else [], start=1):
            row = dict(item or {})
            candidate_id = row.get("candidate_id") or row.get("hallmark_id") or f"h_{source_packet_id}_{i}"
            label = str(row.get("label") or row.get("name") or "unknown_hallmark")
            rows.append(
                {
                    "candidate_id": str(candidate_id),
                    "label": label,
                    "normalized_label": str(row.get("normalized_label") or label),
                    "description": str(row.get("description") or row.get("rationale") or ""),
                    "evidence_scope": str(row.get("evidence_scope") or "disease_level"),
                    "supporting_source_packet_ids": self._packet_ids(row.get("supporting_source_packet_ids"), source_packet_id),
                    "supporting_source_document_ids": self._as_str_list(row.get("supporting_source_document_ids", [])),
                    "supporting_spans": row.get("supporting_spans", []),
                    "candidate_confidence": self._confidence(row.get("candidate_confidence", row.get("confidence"))),
                    "status": self._status(row.get("status")),
                }
            )
        return rows

    def _adapt_modules(self, items: Any, source_packet_id: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for i, item in enumerate(items if isinstance(items, list) else [], start=1):
            row = dict(item or {})
            candidate_id = row.get("candidate_id") or row.get("module_id") or f"m_{source_packet_id}_{i}"
            label = str(row.get("label") or row.get("module_label") or row.get("name") or "unknown_module")
            rows.append(
                {
                    "candidate_id": str(candidate_id),
                    "label": label,
                    "normalized_label": str(row.get("normalized_label") or label),
                    "description": str(row.get("description") or row.get("rationale") or ""),
                    "module_type": self._module_type(row.get("module_type")),
                    "hallmark_links": self._as_str_list(row.get("hallmark_links", [])),
                    "key_genes": self._as_str_list(row.get("key_genes", row.get("genes", []))),
                    "process_terms": self._as_str_list(row.get("process_terms", [])),
                    "supporting_source_packet_ids": self._packet_ids(row.get("supporting_source_packet_ids"), source_packet_id),
                    "supporting_source_document_ids": self._as_str_list(row.get("supporting_source_document_ids", [])),
                    "candidate_confidence": self._confidence(row.get("candidate_confidence", row.get("confidence"))),
                    "status": self._status(row.get("status")),
                }
            )
        return rows

    def _adapt_module_relations(self, items: Any, source_packet_id: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for i, item in enumerate(items if isinstance(items, list) else [], start=1):
            row = dict(item or {})
            candidate_id = row.get("candidate_id") or row.get("relation_id") or f"r_{source_packet_id}_{i}"
            rows.append(
                {
                    "candidate_id": str(candidate_id),
                    "subject_module": str(row.get("subject_module") or row.get("subject") or ""),
                    "predicate": self._predicate(row.get("predicate")),
                    "object_module": str(row.get("object_module") or row.get("object") or ""),
                    "description": str(row.get("description") or ""),
                    "supporting_source_packet_ids": self._packet_ids(row.get("supporting_source_packet_ids"), source_packet_id),
                    "supporting_source_document_ids": self._as_str_list(row.get("supporting_source_document_ids", [])),
                    "candidate_confidence": self._confidence(row.get("candidate_confidence", row.get("confidence"))),
                }
            )
        return rows

    def _adapt_causal_chains(self, items: Any, source_packet_id: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for i, item in enumerate(items if isinstance(items, list) else [], start=1):
            row = dict(item or {})
            candidate_id = row.get("candidate_id") or row.get("chain_id") or f"c_{source_packet_id}_{i}"
            module_label = str(row.get("module_label") or row.get("module") or "")
            steps = row.get("steps", [])
            norm_steps = []
            for j, step in enumerate(steps if isinstance(steps, list) else [], start=1):
                step_row = dict(step or {})
                norm_steps.append(
                    {
                        "order": int(step_row.get("order", j)),
                        "event_label": str(step_row.get("event_label") or step_row.get("event") or ""),
                    }
                )
            rows.append(
                {
                    "candidate_id": str(candidate_id),
                    "title": str(row.get("title") or "causal_chain"),
                    "module_label": module_label,
                    "steps": norm_steps,
                    "trigger_examples": self._as_str_list(row.get("trigger_examples", [])),
                    "supporting_source_packet_ids": self._packet_ids(row.get("supporting_source_packet_ids"), source_packet_id),
                    "supporting_source_document_ids": self._as_str_list(row.get("supporting_source_document_ids", [])),
                    "candidate_confidence": self._confidence(row.get("candidate_confidence", row.get("confidence"))),
                    "status": self._status(row.get("status")),
                }
            )
        return rows

    def _adapt_key_genes(self, items: Any, source_packet_id: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for i, item in enumerate(items if isinstance(items, list) else [], start=1):
            row = dict(item or {})
            candidate_id = row.get("candidate_id") or row.get("gene_id") or f"g_{source_packet_id}_{i}"
            rows.append(
                {
                    "candidate_id": str(candidate_id),
                    "symbol": str(row.get("symbol") or row.get("gene_symbol") or row.get("label") or ""),
                    "gene_role": self._gene_role(row.get("gene_role")),
                    "linked_modules": self._as_str_list(row.get("linked_modules", row.get("modules", []))),
                    "rationale": str(row.get("rationale") or row.get("description") or ""),
                    "supporting_source_packet_ids": self._packet_ids(row.get("supporting_source_packet_ids"), source_packet_id),
                    "supporting_source_document_ids": self._as_str_list(row.get("supporting_source_document_ids", [])),
                    "candidate_confidence": self._confidence(row.get("candidate_confidence", row.get("confidence"))),
                    "status": self._status(row.get("status")),
                }
            )
        return rows

    @staticmethod
    def _adapt_extraction_quality(item: Any) -> Dict[str, Any]:
        row = dict(item or {})
        return {
            "llm_confidence": float(row.get("llm_confidence", row.get("confidence", 0.0)) or 0.0),
            "needs_manual_review": bool(row.get("needs_manual_review", False)),
            "warnings": [str(x) for x in (row.get("warnings", []) or [])],
            "parse_status": str(row.get("parse_status") or "ok"),
            "schema_validation_status": str(row.get("schema_validation_status") or "ok"),
        }

    @staticmethod
    def _confidence(value: Any) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, v))

    @staticmethod
    def _as_str_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(x) for x in value if x is not None]

    @staticmethod
    def _packet_ids(value: Any, fallback_packet_id: str) -> List[str]:
        packet_ids = ExtractionAdapter._as_str_list(value)
        if fallback_packet_id not in packet_ids:
            packet_ids.append(fallback_packet_id)
        return packet_ids

    @staticmethod
    def _status(value: Any) -> str:
        key = str(value or "candidate").strip().lower().replace("_", "-")
        if key in {"candidate", "provisional"}:
            return key
        if key in {"core-draft", "filtered"}:
            return "provisional"
        return "candidate"

    @staticmethod
    def _module_type(value: Any) -> str:
        key = str(value or "supporting_module").strip().lower().replace(" ", "_")
        return key if key in _ALLOWED_MODULE_TYPES else "supporting_module"

    @staticmethod
    def _predicate(value: Any) -> str:
        key = str(value or "linked_to").strip().lower().replace(" ", "_")
        return key if key in _ALLOWED_PREDICATES else "linked_to"

    @staticmethod
    def _gene_role(value: Any) -> str:
        key = str(value or "uncertain").strip().lower().replace(" ", "_")
        return key if key in _ALLOWED_GENE_ROLES else "uncertain"
