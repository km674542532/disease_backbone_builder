from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from app.schemas.base import SchemaModel

MatchType = Literal["exact", "alias", "previous_symbol", "fuzzy", "unresolved"]


class StandardSourceMetadata(SchemaModel):
    authority_name: str
    source_version: str = "unknown"
    snapshot_date: str = "unknown"
    file_path: str = ""


class NormalizationCandidate(SchemaModel):
    normalized_id: str = ""
    normalized_label: str = ""
    source_authority: str = ""
    confidence: float = 0.0


class NormalizationResult(SchemaModel):
    normalized_id: str = ""
    normalized_label: str = ""
    source_authority: str = ""
    source_version: str = "unknown"
    match_type: MatchType = "unresolved"
    confidence: float = 0.0
    candidates: List[NormalizationCandidate] = Field(default_factory=list)
    qa_flags: List[str] = Field(default_factory=list)
    raw_input: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiseaseNormalizationPayload(SchemaModel):
    normalized_label: str = ""
    ids: Dict[str, Optional[str]] = Field(default_factory=dict)
    synonyms: List[str] = Field(default_factory=list)
    source_authorities_used: List[str] = Field(default_factory=list)
    conflict: Optional[str] = None
    qa_flags: List[str] = Field(default_factory=list)
