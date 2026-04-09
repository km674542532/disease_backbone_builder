"""Unified LLM client abstraction for structured extraction."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
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


class QwenAPIClient:
    """Minimal OpenAI-compatible chat completion client for Qwen models."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = base_url or os.getenv(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        )
        self.model = model or os.getenv("QWEN_MODEL", "qwen-max")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("QWEN_API_KEY (or DASHSCOPE_API_KEY) is required for QwenAPIClient")

    def generate_json(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are an extraction engine. Return strict JSON object only."},
                {"role": "user", "content": prompt},
            ],
        }
        req = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # pragma: no cover - network branch
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Qwen API HTTPError {exc.code}: {detail[:300]}") from exc
        except Exception as exc:  # pragma: no cover - network branch
            raise RuntimeError(f"Qwen API request failed: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise TypeError("Qwen response JSON is not an object")
            return parsed
        except Exception as exc:
            raise RuntimeError(f"Failed to parse Qwen response as JSON object: {body}") from exc
