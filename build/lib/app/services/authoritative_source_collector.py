"""Authoritative source normalization/collection for Disease Backbone Builder v1.1 MVP."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.schemas.source_document import SourceDocument, SourceLocator
from app.utils.json_io import write_json

logger = logging.getLogger(__name__)

RAW_SOURCE_DIR = Path("data/raw_sources")
SOURCE_MANIFEST_PATH = Path("data/source_manifest.json")


def _audit(stage: str, status: str, **kwargs: Any) -> None:
    payload = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info("audit stage=%s status=%s %s", stage, status, payload)


def _stable_id(disease_label: str, source_type: str, source_title: str, locator: SourceLocator) -> str:
    key = f"{disease_label}|{source_type}|{source_title}|{locator.model_dump_json()}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"src-{digest}"


def _coerce_payload(input_data: Any) -> Dict[str, Any]:
    if isinstance(input_data, dict):
        return input_data
    if isinstance(input_data, str):
        path = Path(input_data)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".json":
                payload = json.loads(text)
                if isinstance(payload, dict):
                    return payload
                return {"content": payload, "source_locator": {"internal_ref": str(path)}}
            return {"content": text, "source_locator": {"internal_ref": str(path)}, "source_title": path.name}
        return {"content": input_data}
    raise TypeError(f"Unsupported source input type: {type(input_data)!r}")


def _build_authoritative_document(
    *,
    disease_label: str,
    source_type: str,
    source_name: str,
    default_title: str,
    default_locator: Optional[Dict[str, str]],
    input_data: Any,
) -> SourceDocument:
    payload = _coerce_payload(input_data)
    locator_data = {**(default_locator or {}), **payload.get("source_locator", {})}
    locator = SourceLocator.model_validate(locator_data)
    source_title = payload.get("source_title") or default_title
    normalized = SourceDocument(
        source_document_id=_stable_id(disease_label, source_type, source_title, locator),
        disease_label=disease_label,
        source_type=source_type,
        source_name=source_name,
        source_title=source_title,
        source_locator=locator,
        priority_tier="authoritative",
        selection_metadata={"status": "provisional", "source_class": "authoritative"},
        metadata={
            "content": payload.get("content", ""),
            "snippet": payload.get("snippet", ""),
            "sections": payload.get("sections", []),
            "status": "draft",
        },
    )
    return normalized


def _persist_raw_source(doc: SourceDocument) -> Path:
    RAW_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_SOURCE_DIR / f"{doc.source_document_id}.json"
    write_json(target, doc.model_dump())
    return target


def collect_gene_reviews_source(disease_label: str, input_data: Any) -> SourceDocument:
    stage = "authoritative_source_collection.gene_reviews"
    _audit(stage, "started", disease=disease_label)
    try:
        doc = _build_authoritative_document(
            disease_label=disease_label,
            source_type="GeneReviews",
            source_name="GeneReviews",
            default_title=f"{disease_label} - GeneReviews mechanism/pathogenesis",
            default_locator={"url": "https://www.ncbi.nlm.nih.gov/books/NBK1116/"},
            input_data=input_data,
        )
        raw_path = _persist_raw_source(doc)
        _audit(stage, "completed", source_document_id=doc.source_document_id, path=raw_path)
        return doc
    except Exception:
        _audit(stage, "failed", disease=disease_label)
        raise


def collect_orphanet_source(disease_label: str, input_data: Any) -> SourceDocument:
    stage = "authoritative_source_collection.orphanet"
    _audit(stage, "started", disease=disease_label)
    try:
        doc = _build_authoritative_document(
            disease_label=disease_label,
            source_type="Orphanet",
            source_name="Orphanet",
            default_title=f"{disease_label} - Orphanet summary",
            default_locator={"url": "https://www.orpha.net"},
            input_data=input_data,
        )
        raw_path = _persist_raw_source(doc)
        _audit(stage, "completed", source_document_id=doc.source_document_id, path=raw_path)
        return doc
    except Exception:
        _audit(stage, "failed", disease=disease_label)
        raise


def collect_authoritative_sources(
    disease_label: str,
    gene_reviews_inputs: Optional[Iterable[Any]] = None,
    orphanet_inputs: Optional[Iterable[Any]] = None,
) -> List[SourceDocument]:
    stage = "authoritative_source_collection"
    _audit(stage, "started", disease=disease_label)
    try:
        docs: List[SourceDocument] = []
        for item in gene_reviews_inputs or []:
            docs.append(collect_gene_reviews_source(disease_label, item))
        for item in orphanet_inputs or []:
            docs.append(collect_orphanet_source(disease_label, item))

        manifest = {
            "disease_label": disease_label,
            "status": "draft",
            "authoritative_source_document_ids": [d.source_document_id for d in docs],
            "sources": [d.model_dump() for d in docs],
        }
        write_json(SOURCE_MANIFEST_PATH, manifest)
        _audit(stage, "completed", disease=disease_label, source_count=len(docs), manifest=SOURCE_MANIFEST_PATH)
        return docs
    except Exception:
        _audit(stage, "failed", disease=disease_label)
        raise
