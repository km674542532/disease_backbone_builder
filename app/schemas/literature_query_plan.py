"""Schema for PubMed review query planning."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import ConfigDict

from app.schemas.base import SchemaModel


class QueryDateRange(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    start_year: int
    end_year: int


class LiteratureQueryPlan(SchemaModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    disease_label: str
    query_family: Literal["review_discovery", "systematic_review_discovery", "mechanism_review_discovery"]
    query_string: str
    date_range: QueryDateRange
    language_filter: List[str]
    max_results: int
    priority: int
    notes: Optional[str] = None
