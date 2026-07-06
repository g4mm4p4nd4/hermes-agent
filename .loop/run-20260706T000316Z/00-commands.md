# Phase 0 Command Baseline

Run id: `20260706T000316Z`
Repo: `/Users/mnm/Documents/Github/hermes-agent`
Shell: `zsh`

## Environment

- Branch: `main`
- Head: `f289cf97d63ae052dac5cce9ae785a58190da877`
- Upstream: `origin/main`
- Status at discovery: `main...origin/main [ahead 2]`
- Python env present: `venv`
- `.venv` absent locally; CI creates `.venv`, but repo guidance says to activate `venv`.

## TEST_CMD

Source: `.github/workflows/tests.yml:34-42`, `pyproject.toml:98-103`.

```bash
source venv/bin/activate && OPENROUTER_API_KEY="" OPENAI_API_KEY="" NOUS_API_KEY="" python -m pytest tests/ -q --ignore=tests/integration --tb=short -n auto
```

Result: pass.

Observed output excerpt:

```text
6351 passed, 164 skipped, 110 warnings in 65.87s (0:01:05)
```

Notes:
- Warnings are mostly unawaited coroutine/resource warnings in ACP/gateway/MCP tests plus aiohttp `NotAppKeyWarning` and httpx `verify=<str>` deprecations.
- No failures.

## LINT_CMD

No Python lint command is configured in `pyproject.toml`, root `package.json`, or CI. A docs-only lint exists for website changes.

Source: `.github/workflows/docs-site-checks.yml:33-39`, `website/package.json`.

```bash
cd website && npm run lint:diagrams
```

Result: blocked locally.

Observed output:

```text
> website@0.0.0 lint:diagrams
> ascii-guard lint docs

sh: ascii-guard: command not found
```

Interpretation: CI installs `ascii-guard` immediately before running this command; local env does not currently have it on PATH.

## RUN_CMD

Source: `README.md:49-60`, `pyproject.toml:87-90`.

```bash
source venv/bin/activate && hermes --help
```

Result: pass.

Observed output excerpt:

```text
Hermes Agent - AI assistant with tool-calling capabilities
{chat,model,gateway,setup,whatsapp,login,logout,status,cron,doctor,config,pairing,skills,plugins,honcho,tools,mcp,sessions,insights,claw,version,update,uninstall,acp}
```

## OTHER_CI_COMMANDS

Nix workflow is path-scoped for `flake.nix`, `flake.lock`, `nix/**`, `pyproject.toml`, `uv.lock`, `hermes_cli/**`, `run_agent.py`, and `acp_adapter/**`.

Source: `.github/workflows/nix.yml:1-40`.

```bash
command -v nix && nix flake show --json > /tmp/hermes-nix-flake-show.json
```

Result: blocked locally; `nix` was not found on PATH.

Docs-site build is path-scoped for `website/**` and depends on `npm ci` in `website`.

Source: `.github/workflows/docs-site-checks.yml:1-39`.

Not executed in Phase 0 because no docs-site task is active and the docs lint prerequisite is missing locally.
