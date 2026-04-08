"""Create SourcePacket objects from SourceDocument objects."""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from app.schemas.source_document import SourceDocument
from app.schemas.source_packet import SourcePacket
from app.utils.json_io import write_json, write_jsonl

logger = logging.getLogger(__name__)


class Packetizer:
    """Section/subsection/paragraph-group aware packetizer."""

    def packetize(self, disease_label: str, source_docs: Iterable[Dict[str, Any] | SourceDocument]) -> List[SourcePacket]:
        docs = [self._coerce_doc(disease_label, d) for d in source_docs]
        logger.info("audit stage=source_packetization status=started docs=%d", len(docs))

        packets: List[SourcePacket] = []
        per_source_count: Dict[str, int] = defaultdict(int)
        skipped_empty = 0

        for doc in docs:
            section_items = self._extract_sections(doc)
            for section_label, text_block in section_items:
                clean = text_block.strip()
                if not clean:
                    skipped_empty += 1
                    continue
                packet = SourcePacket(
                    source_packet_id=f"sp_{len(packets)+1:04d}",
                    source_document_id=doc.source_document_id,
                    disease_label=disease_label,
                    source_type=doc.source_type,
                    source_name=doc.source_name,
                    source_title=doc.source_title,
                    section_label=section_label,
                    text_block=clean,
                    priority_tier=doc.priority_tier,
                    selection_metadata=doc.selection_metadata,
                    metadata=doc.metadata,
                )
                packets.append(packet)
                per_source_count[doc.source_document_id] += 1

        avg_length = sum(len(p.text_block) for p in packets) / len(packets) if packets else 0.0
        stats = {
            "source_packet_counts": dict(per_source_count),
            "average_packet_length": round(avg_length, 2),
            "skipped_empty_packets": skipped_empty,
            "packet_count": len(packets),
        }
        write_jsonl("data/source_packets/source_packets.jsonl", [p.model_dump() for p in packets])
        write_json("data/source_packets/packetization_stats.json", stats)
        logger.info("audit stage=source_packetization status=completed packets=%d skipped_empty=%d", len(packets), skipped_empty)
        return packets

    @staticmethod
    def _coerce_doc(disease_label: str, payload: Dict[str, Any] | SourceDocument) -> SourceDocument:
        if isinstance(payload, SourceDocument):
            return payload
        if "source_locator" in payload and "priority_tier" in payload:
            return SourceDocument.model_validate(payload)

        title = payload.get("source_title", "untitled")
        fallback_id = f"src_{title.lower().replace(' ', '_')}"
        metadata = dict(payload.get("metadata", {}))
        metadata.setdefault("sections", payload.get("sections", []))
        metadata.setdefault("content", payload.get("text_block", ""))

        return SourceDocument(
            source_document_id=payload.get("source_document_id", fallback_id),
            disease_label=payload.get("disease_label", disease_label),
            source_type=payload.get("source_type", "Other"),
            source_name=payload.get("source_name", payload.get("source_title", "unknown_source")),
            source_title=title,
            source_locator=payload.get("source_locator", {}),
            priority_tier=payload.get("priority_tier", payload.get("source_priority_tier", "supplementary_review")),
            selection_metadata=payload.get("selection_metadata", {}),
            metadata=metadata,
        )

    def _extract_sections(self, doc: SourceDocument) -> List[Tuple[str, str]]:
        sections = doc.metadata.get("sections", [])
        if sections:
            extracted: List[Tuple[str, str]] = []
            for sec in sections:
                section_label = sec.get("section_label", "section")
                subsections = sec.get("subsections", [])
                if subsections:
                    for sub in subsections:
                        extracted.extend(
                            self._paragraph_groups(
                                f"{section_label} / {sub.get('label', 'subsection')}",
                                sub.get("text", ""),
                            )
                        )
                else:
                    extracted.extend(self._paragraph_groups(section_label, sec.get("text", "")))
            return extracted

        content = doc.metadata.get("content") or doc.metadata.get("abstract") or ""
        return self._paragraph_groups("main", content)

    @staticmethod
    def _paragraph_groups(section_label: str, text: str) -> List[Tuple[str, str]]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
        if not paragraphs:
            return [(section_label, text or "")]
        return [(f"{section_label} / paragraph_group_{i}", paragraph) for i, paragraph in enumerate(paragraphs, start=1)]
