from unittest.mock import MagicMock, patch

from run_agent import AIAgent


def _make_agent(monkeypatch, session_db, *, platform="cli", source=None):
    if source is None:
        monkeypatch.delenv("HERMES_SESSION_SOURCE", raising=False)
    else:
        monkeypatch.setenv("HERMES_SESSION_SOURCE", source)

    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        return AIAgent(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            model="test/model",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            session_db=session_db,
            session_id="source-test-session",
            platform=platform,
        )


def test_explicit_session_source_overrides_cli_platform(monkeypatch):
    session_db = MagicMock()
    agent = _make_agent(monkeypatch, session_db, platform="cli", source="paperclip")

    agent._ensure_db_session()

    assert session_db.create_session.call_args.kwargs["source"] == "paperclip"


def test_platform_is_session_source_without_explicit_override(monkeypatch):
    session_db = MagicMock()
    agent = _make_agent(monkeypatch, session_db, platform="cli")

    agent._ensure_db_session()

    assert session_db.create_session.call_args.kwargs["source"] == "cli"
