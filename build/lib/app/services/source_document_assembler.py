"""Assemble authoritative + selected review records into SourceDocument collection."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Dict, List

from app.schemas.literature_record import LiteratureRecord
from app.schemas.review_selection_record import ReviewSelectionRecord
from app.schemas.source_document import SourceDocument, SourceLocator
from app.utils.json_io import write_json

logger = logging.getLogger(__name__)


class SourceDocumentAssembler:
    @staticmethod
    def _source_document_id(disease_label: str, source_type: str, locator: SourceLocator) -> str:
        locator_key = locator.pmid or locator.doi or locator.url or locator.internal_ref or "na"
        slug = disease_label.lower().replace(" ", "_")
        prefix = source_type.lower().replace(" ", "_")
        digest = hashlib.sha1(f"{disease_label}|{source_type}|{locator_key}".encode("utf-8")).hexdigest()[:8]
        return f"src_{slug}_{prefix}_{digest}"

    def assemble(
        self,
        disease_label: str,
        authoritative_source_docs: List[SourceDocument],
        selected_review_records: List[ReviewSelectionRecord],
        literature_record_map: Dict[str, LiteratureRecord],
    ) -> List[SourceDocument]:
        logger.info("audit stage=source_manifest_freeze status=started disease=%s", disease_label)
        docs = list(authoritative_source_docs)

        for sel in selected_review_records:
            if sel.decision != "selected":
                continue
            literature = literature_record_map.get(sel.pmid)
            if literature is None:
                continue

            source_type = {
                "anchor_review": "ReviewArticle",
                "systematic_review": "SystematicReview",
                "specialized_review": "SpecializedReview",
                "supplementary_review": "ReviewArticle",
                "rejected": "Other",
            }[sel.review_bucket]
            locator = SourceLocator(
                pmid=literature.pmid,
                doi=literature.doi,
                url=literature.pubmed_url,
                internal_ref=f"pubmed:{literature.pmid}",
            )
            doc = SourceDocument(
                source_document_id=self._source_document_id(disease_label, source_type, locator),
                disease_label=disease_label,
                source_type=source_type,
                source_name=literature.journal,
                source_title=literature.title,
                source_locator=locator,
                priority_tier=sel.review_bucket,
                selection_metadata=sel.model_dump(),
                metadata={
                    "status": "candidate",
                    "abstract": literature.abstract,
                    "authors": literature.authors,
                    "publication_year": literature.publication_year,
                    "publication_types": literature.publication_types,
                    "mesh_terms": literature.mesh_terms,
                },
            )
            docs.append(doc)

        manifest = {
            "disease_label": disease_label,
            "authoritative_source_document_ids": [d.source_document_id for d in docs if d.priority_tier == "authoritative"],
            "selected_review_source_document_ids": [d.source_document_id for d in docs if d.priority_tier != "authoritative"],
            "source_count": len(docs),
        }
        write_json(Path("data") / "source_manifest.json", manifest)
        logger.info("audit stage=source_manifest_freeze status=completed disease=%s source_count=%d", disease_label, len(docs))
        return docs
