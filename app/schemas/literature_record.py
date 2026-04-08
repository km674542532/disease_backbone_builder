"""Schema for literature records from PubMed retrieval."""
from __future__ import annotations

from typing import List, Optional

from pydantic import ConfigDict, Field

from app.schemas.base import SchemaModel


class LiteratureRecord(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    literature_id: str
    pmid: str
    doi: Optional[str] = None
    title: str
    journal: str
    publication_year: int
    abstract: str
    authors: List[str] = Field(default_factory=list)
    publication_types: List[str] = Field(default_factory=list)
    mesh_terms: List[str] = Field(default_factory=list)
    language: str = "eng"
    pubmed_url: Optional[str] = None
    retrieval_query_id: str
    retrieval_source: str = "pubmed_api"
    is_review_like: bool = True
