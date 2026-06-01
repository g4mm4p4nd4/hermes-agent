# Hermes Baseline Audit

- Commit SHA: `4c100e48fcde457ff8b9b3738f65729f567ca604`
- Branch at audit start: `main`
- Remote origin: `https://github.com/g4mm4p4nd4/hermes-agent.git`
- Upstreams: no separate upstream remote configured
- Local changes at audit start: none
- Ahead/behind after fetch: `0/0` against `origin/main`
- Tags/releases: no local git tags listed

## Existing Paperclip Adapter Files

No first-party Paperclip-specific adapter package exists in this checkout. Prior Paperclip/Hermes behavior is known to live at the external adapter boundary, not as a core Hermes package. This branch therefore adds Portfolio-OS support as a sidecar adapter and does not delete or rewrite current adapter/gateway behavior.

## Existing Portfolio-OS Integration Files

No existing `pos.hermes_task_bundle.v1` contract or `portfolio-os` CLI namespace existed before this implementation.

## CLI Entry Points

- `pyproject.toml` exposes `hermes = hermes_cli.main:main`
- repo wrapper `./hermes` launches the legacy Fire-based terminal CLI
- new wrapper `./bin/hermes` launches the Portfolio-OS adapter namespace
- new installed namespace: `hermes portfolio-os ...`

## Approval / Tooling Primitives

- `tools/approval.py` is the central dangerous-command approval system.
- `acp_adapter/permissions.py` bridges ACP permission requests into Hermes approval callbacks.
- `gateway/run.py` contains messaging approval flows for `/approve` and `/deny`.

## Agent Runtime Primitives

- `agent/auxiliary_client.py`
- `agent/prompt_builder.py`
- `agent/skill_commands.py`
- `run_agent.py`
- `environments/**`
- `tools/**`

## Gateway / Platform Adapter Primitives

- `gateway/platforms/api_server.py`
- `gateway/platforms/{discord,slack,telegram,whatsapp,email,sms,webhook}.py`
- `gateway/run.py`
- `gateway/session.py`

## Scripts / Skills / Optional Skills Relevant To Execution

- `scripts/hermes-gateway`
- `scripts/install.sh`
- `skills/**`
- `optional-skills/**`
- `tools/file_tools.py`
- `tools/terminal_tool.py`
- `tools/approval.py`

## Existing Tests And Test Command

The repo has broad pytest coverage under `tests/`. Relevant baseline areas include CLI, gateway, ACP, approval, file safety, terminal safety, and runtime provider tests.

Recommended command for this adapter slice:

```bash
pytest tests/test_portfolio_os_adapter.py
```

The broader suite remains:

```bash
pytest
```

## Risks If Upgraded Blindly

- Paperclip/Hermes behavior is adapter-boundary sensitive; deleting local behavior without compatibility tests can break live Paperclip model/skill routing.
- Existing approval and command-safety behavior spans CLI, ACP, gateway, and terminal tools.
- Gateway/session behavior has extensive tests and should not be refactored for this adapter.
- The repo has no tag boundary to select a release upgrade from; origin/main is already current.

## Upgrade Recommendation

Recommendation: **do not upgrade**.

Reason: local `main` is already aligned with `origin/main`, no tags/releases are present, and no upstream remote is configured. The correct path is `feature/hermes-portfolio-os-adapter-v1`: add a side-by-side Portfolio-OS adapter while preserving all existing Hermes runtime, gateway, ACP, approval, skills, and optional skills behavior.
