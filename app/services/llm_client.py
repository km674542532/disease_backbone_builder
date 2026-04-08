"""Unified LLM client abstraction for structured extraction."""
from __future__ import annotations

import json
from typing import Protocol


class LLMClient(Protocol):
    """Protocol for project-wide LLM invocation."""

    def generate_json(self, prompt: str) -> dict:
        ...


class MockLLMClient:
    """Deterministic JSON client for tests and offline MVP."""

    def __init__(self, response_json: dict | None = None):
        self._response_json = response_json or {
            "hallmarks": [],
            "modules": [],
            "module_relations": [],
            "causal_chains": [],
            "key_genes": [],
            "global_notes": [],
            "extraction_quality": {
                "llm_confidence": 0.5,
                "needs_manual_review": False,
                "warnings": [],
            },
        }

    def generate_json(self, prompt: str) -> dict:
        _ = prompt
        return json.loads(json.dumps(self._response_json))
