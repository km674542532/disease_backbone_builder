"""Shared helpers for strict serializable schema models."""
from __future__ import annotations

from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="SchemaModel")


class SchemaModel(BaseModel):
    """Strict base schema with convenience serialization helpers."""

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_dict(cls: Type[T], payload: Dict[str, Any]) -> T:
        return cls.model_validate(payload)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
