"""Create SourcePacket objects from collected source docs."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.schemas.source_packet import SourcePacket

logger = logging.getLogger(__name__)


class Packetizer:
    """Section/subsection aware packetizer."""

    def packetize(self, disease_label: str, source_docs: List[Dict[str, Any]]) -> List[SourcePacket]:
        logger.info("stage_start packetize docs=%d", len(source_docs))
        packets: List[SourcePacket] = []
        idx = 1
        for doc in source_docs:
            sections = doc.get("sections", [])
            if not sections and doc.get("text_block"):
                sections = [{"section_label": doc.get("section_label", "main"), "text": doc["text_block"]}]
            for sec in sections:
                subsection_list = sec.get("subsections")
                if subsection_list:
                    for sub in subsection_list:
                        packets.append(
                            self._make_packet(disease_label, doc, f"{sec.get('section_label','section')} / {sub.get('label','subsection')}", sub.get("text", ""), idx)
                        )
                        idx += 1
                else:
                    packets.append(
                        self._make_packet(disease_label, doc, sec.get("section_label", "section"), sec.get("text", ""), idx)
                    )
                    idx += 1
        logger.info("stage_end packetize packets=%d", len(packets))
        return packets

    def _make_packet(self, disease_label: str, doc: Dict[str, Any], section_label: str, text: str, idx: int) -> SourcePacket:
        return SourcePacket(
            source_packet_id=f"sp_{idx:04d}",
            source_document_id=doc.get("source_document_id", f"src_{idx:04d}"),
            disease_label=disease_label,
            source_type=doc.get("source_type", "Other"),
            source_name=doc.get("source_name", doc.get("source_title", "unknown_source")),
            source_title=doc.get("source_title", "untitled"),
            source_priority_tier=doc.get("source_priority_tier", "supplementary_review"),
            selection_metadata=doc.get("selection_metadata", {}),
            section_label=section_label,
            text_block=text,
            metadata=doc.get("metadata", {}),
        )
