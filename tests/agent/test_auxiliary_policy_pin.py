"""Policy-owned auxiliary routing must never switch provider/model."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import auxiliary_client as aux


def _response(content: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture(autouse=True)
def _policy_pinned(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HERMES_POLICY_PINNED_ROUTE", "1")
    monkeypatch.setenv("HERMES_DISABLE_FALLBACK_MODEL", "1")
    aux.clear_runtime_main()
    aux.set_runtime_main(
        "zai",
        "glm-5.1",
        base_url="https://pinned.example/v1",
        api_key="pinned-test-key",
        api_mode="chat_completions",
    )
    yield
    aux.clear_runtime_main()


def test_auto_resolution_fails_before_any_fallback_chain(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(aux, "resolve_provider_client", lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(
        aux,
        "_try_configured_fallback_chain",
        lambda *args, **kwargs: pytest.fail("configured fallback must not run"),
    )
    monkeypatch.setattr(
        aux,
        "_try_main_fallback_chain",
        lambda *args, **kwargs: pytest.fail("main fallback must not run"),
    )
    monkeypatch.setattr(
        aux,
        "_get_provider_chain",
        lambda: pytest.fail("built-in auto discovery must not run"),
    )

    with pytest.raises(aux.AuxiliaryCapabilityMismatchError) as exc:
        aux._resolve_auto(task="compression")

    assert exc.value.error_code == "provider_capability_mismatch"


def test_sync_call_ignores_task_override_and_uses_exact_main_route(
    monkeypatch: pytest.MonkeyPatch,
):
    client = MagicMock()
    client.base_url = "https://pinned.example/v1"
    client.chat.completions.create.return_value = _response("pinned")
    captured = {}

    def _cached(provider, model=None, *args, **kwargs):
        captured.update(provider=provider, model=model, kwargs=kwargs)
        return client, model

    monkeypatch.setattr(aux, "_get_cached_client", _cached)
    monkeypatch.setattr(
        aux,
        "_resolve_task_provider_model",
        lambda *args, **kwargs: ("openrouter", "fallback-model", None, None, None),
    )

    result = aux.call_llm(
        task="compression",
        provider="openrouter",
        model="fallback-model",
        main_runtime={
            "provider": "zai",
            "model": "glm-5.1",
            "base_url": "https://pinned.example/v1",
            "api_key": "pinned-test-key",
            "api_mode": "chat_completions",
        },
        messages=[{"role": "user", "content": "summarize"}],
    )

    assert result.choices[0].message.content == "pinned"
    assert captured["provider"] == "zai"
    assert captured["model"] == "glm-5.1"
    assert captured["kwargs"]["base_url"] == "https://pinned.example/v1"
    assert captured["kwargs"]["api_key"] == "pinned-test-key"


def test_unavailable_pinned_route_never_consults_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(aux, "_get_cached_client", lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(
        aux,
        "_try_configured_fallback_for_unavailable_client",
        lambda *args, **kwargs: pytest.fail("fallback must not run"),
    )

    with pytest.raises(aux.AuxiliaryCapabilityMismatchError):
        aux.call_llm(
            task="title_generation",
            messages=[{"role": "user", "content": "title"}],
        )


def test_vision_unavailable_fails_instead_of_auto_switching(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []

    def _vision(**kwargs):
        calls.append(kwargs)
        return "zai", None, None

    monkeypatch.setattr(aux, "resolve_vision_provider_client", _vision)

    with pytest.raises(aux.AuxiliaryCapabilityMismatchError):
        aux.call_llm(
            task="vision",
            messages=[{"role": "user", "content": "inspect image"}],
        )

    assert len(calls) == 1
    assert calls[0]["provider"] == "zai"
    assert calls[0]["model"] == "glm-5.1"


@pytest.mark.asyncio
async def test_async_call_uses_exact_main_route(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    client.base_url = "https://pinned.example/v1"
    client.chat.completions.create = AsyncMock(return_value=_response("async pinned"))
    captured = {}

    def _cached(provider, model=None, *args, **kwargs):
        captured.update(provider=provider, model=model, kwargs=kwargs)
        return client, model

    monkeypatch.setattr(aux, "_get_cached_client", _cached)

    result = await aux.async_call_llm(
        task="session_search",
        provider="openrouter",
        model="fallback-model",
        main_runtime={
            "provider": "zai",
            "model": "glm-5.1",
            "base_url": "https://pinned.example/v1",
            "api_key": "pinned-test-key",
            "api_mode": "chat_completions",
        },
        messages=[{"role": "user", "content": "search"}],
    )

    assert result.choices[0].message.content == "async pinned"
    assert captured["provider"] == "zai"
    assert captured["model"] == "glm-5.1"
