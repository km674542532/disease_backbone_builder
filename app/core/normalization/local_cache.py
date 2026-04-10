from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from app.core.normalization.base import StandardSourceMetadata

logger = logging.getLogger(__name__)


class LocalStandardCache:
    def __init__(self) -> None:
        self._payload_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._meta_cache: Dict[str, StandardSourceMetadata] = {}

    def load_json_records(self, authority: str, file_path: str, source_version: str = "unknown", snapshot_date: str = "unknown") -> List[Dict[str, Any]]:
        key = f"{authority}:{file_path}"
        if key in self._payload_cache:
            return self._payload_cache[key]
        path = Path(file_path)
        if not path.exists():
            logger.warning("standard_snapshot_missing authority=%s file=%s", authority, file_path)
            self._payload_cache[key] = []
            self._meta_cache[key] = StandardSourceMetadata(
                authority_name=authority,
                source_version=source_version,
                snapshot_date=snapshot_date,
                file_path=file_path,
            )
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "records" in payload:
            records = payload["records"]
            source_version = str(payload.get("source_version", source_version))
            snapshot_date = str(payload.get("snapshot_date", snapshot_date))
        elif isinstance(payload, list):
            records = payload
        else:
            records = []
        self._payload_cache[key] = records
        self._meta_cache[key] = StandardSourceMetadata(
            authority_name=authority,
            source_version=source_version,
            snapshot_date=snapshot_date,
            file_path=file_path,
        )
        return records

    def metadata(self, authority: str, file_path: str) -> StandardSourceMetadata:
        key = f"{authority}:{file_path}"
        return self._meta_cache.get(key, StandardSourceMetadata(authority_name=authority, file_path=file_path))
