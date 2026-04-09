import pytest

from app.pipelines.build_backbone import _build_llm_client
from app.services.llm_client import MockLLMClient


def test_build_llm_client_auto_without_key_uses_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    client = _build_llm_client("auto", None)

    assert isinstance(client, MockLLMClient)


def test_build_llm_client_qwen_without_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    with pytest.raises(ValueError):
        _build_llm_client("qwen", None)
