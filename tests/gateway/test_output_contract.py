"""Tests for output budget propagation into gateway AIAgent construction."""

from unittest.mock import patch


def test_runtime_kwargs_reads_output_budget_env_and_config():
    """Output budget values flow into _resolve_runtime_agent_kwargs."""
    fake_config = {
        "output": {
            "max_sentences": 11,
            "max_chars": 333,
        },
    }
    fake_runtime = {
        "api_key": "test-key",
        "base_url": "https://openrouter.ai/api/v1",
        "provider": "openrouter",
        "api_mode": "chat_completions",
        "command": None,
        "args": [],
    }

    with patch("gateway.run._load_gateway_config", return_value=fake_config), \
         patch("hermes_cli.runtime_provider.resolve_runtime_provider", return_value=fake_runtime), \
         patch("hermes_cli.runtime_provider.format_runtime_provider_error", return_value="oops"), \
         patch.dict("os.environ", {"HERMES_OUTPUT_MAX_SENTENCES": "9"}, clear=False):
        from gateway.run import _resolve_runtime_agent_kwargs
        kwargs = _resolve_runtime_agent_kwargs()

    assert kwargs["output_max_sentences"] == 9
    assert kwargs["output_max_chars"] == 333


def test_resolve_turn_config_includes_output_budget():
    """Smart routing does not drop output budget parameters."""
    from gateway.run import GatewayRunner

    runner = GatewayRunner.__new__(GatewayRunner)
    runner._smart_model_routing = {"enabled": False}

    runtime_kwargs = {
        "api_key": "test-key",
        "base_url": "https://openrouter.ai/api/v1",
        "provider": "openrouter",
        "api_mode": "chat_completions",
        "command": None,
        "args": [],
        "output_max_sentences": 4,
        "output_max_chars": 120,
    }
    route = runner._resolve_turn_agent_config("status", "gpt-6.0-test", runtime_kwargs)
    route_runtime = route["runtime"]

    assert route_runtime["output_max_sentences"] == 4
    assert route_runtime["output_max_chars"] == 120
