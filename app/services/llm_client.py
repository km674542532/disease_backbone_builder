"""Unified LLM client abstraction for structured extraction."""
from __future__ import annotations

import json
import os
import time
from typing import Protocol

from openai import OpenAI



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
    """OpenAI SDK-based chat completion client for Qwen-compatible API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 600,
    ) -> None:
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.model = model or "qwen-max"
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("QWEN_API_KEY is required for QwenAPIClient")

        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - import environment
            raise RuntimeError("OpenAI SDK is required for QwenAPIClient") from exc

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )

    def generate_json(self, prompt: str) -> dict:
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are an extraction engine. Return strict JSON object only.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            latency_seconds = time.perf_counter() - start

            usage = response.usage
            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            content = response.choices[0].message.content if response.choices else None

            print(
                "QwenAPIClient response meta "
                f"model={response.model} latency={latency_seconds:.3f}s "
                f"tokens(prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens})"
            )
            print(f"QwenAPIClient response content (debug): {content}")

            try:
                parsed = json.loads(content or "")
            except Exception as parse_exc:
                print(f"QwenAPIClient raw response object: {response}")
                raise RuntimeError(
                    f"Failed to parse Qwen response as JSON object: {parse_exc}"
                ) from parse_exc

            if not isinstance(parsed, dict):
                print(f"QwenAPIClient raw response object: {response}")
                raise RuntimeError("Parsed Qwen response is not a JSON object")

            return parsed
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"Qwen API request failed: {exc}") from exc
