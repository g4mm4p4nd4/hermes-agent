# Hermes Upgrade Decision

## Decision

Do not upgrade. Build the Portfolio-OS adapter side-by-side on `feature/hermes-portfolio-os-adapter-v1`.

## Current Version Compared To Origin

- Local commit: `4c100e48fcde457ff8b9b3738f65729f567ca604`
- `origin/main`: same commit after fetch
- Ahead/behind: `0/0`
- Tags/releases: none listed locally
- Upstream remote: none configured

This checkout is not old relative to `origin/main`.

## Upstream Changes That Matter

No upstream delta exists in the configured remote. There is nothing to merge, rebase, or cherry-pick for this flywheel.

## Official Feature Overlap

Existing Hermes includes useful primitives for:

- approval gates: `tools/approval.py`, ACP permission bridge, gateway approve/deny
- agent runtime: `agent/**`, `run_agent.py`, `environments/**`
- gateway/platform adapters: `gateway/**`
- CLI execution: `hermes_cli/main.py`, repo wrapper `./hermes`
- status/resume concepts: CLI/gateway session resume, cron status, gateway status

It did not include a Portfolio-OS task-bundle namespace, target repo mutation policy, or result artifact schema.

## Recommended Path

- Keep current version.
- Add a side-by-side compatibility adapter.
- Preserve local/external Paperclip adapter behavior.
- Validate with adapter-specific tests before any future upgrade.

## Must Be Preserved

- `acp_adapter/**`
- `agent/**`
- `gateway/**`
- `gateway/platforms/**`
- `hermes_cli/**`
- `honcho_integration/**`
- `tools/approval.py`
- `tools/file_tools.py`
- `tools/terminal_tool.py`
- existing scripts, skills, optional skills, and tests
- external Paperclip/Hermes adapter behavior

## Tests Required Before Accepting Future Upgrade

- `pytest tests/test_portfolio_os_adapter.py`
- existing approval tests
- gateway status/resume/approval tests
- ACP permission tests
- Paperclip external adapter verification when that checkout is present
