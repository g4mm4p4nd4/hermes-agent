# Phase 0 Criteria

Run id: `20260706T000316Z`
Repo: `/Users/mnm/Documents/Github/hermes-agent`
Mode: `review`

## Vision

Hermes Agent is a self-improving, provider-flexible AI agent that runs through CLI, messaging gateways, scheduled automation, delegated subagents, and multiple execution backends while preserving memory, skills, safety, and compact evidence-bearing outputs. Local Portfolio-OS/Paperclip adapter behavior is part of the current checkout's production surface and must remain compatible when touched.

Sources: `README.md:14-25`, `README.md:49-60`, `pyproject.toml:5-10`, `docs/output_contract.md:1-5`, `docs/portfolio_os/adapter_contract.md:1-40`.

## Health Criteria

1. Core non-integration tests pass with the CI command: `source venv/bin/activate && OPENROUTER_API_KEY="" OPENAI_API_KEY="" NOUS_API_KEY="" python -m pytest tests/ -q --ignore=tests/integration --tb=short -n auto`.
   Source: `.github/workflows/tests.yml:34-42`, `pyproject.toml:98-103`.
   Confidence: high.

2. The installed CLI surface remains importable and discoverable through the `hermes` console script, including command groups for chat, model, gateway, setup, cron, tools, sessions, update, and ACP.
   Source: `README.md:49-60`, `pyproject.toml:87-90`.
   Confidence: high.

3. Provider flexibility is preserved: users can switch model/provider without code changes, and provider/routing changes must not silently remove MiniMax, OpenRouter, Nous Portal, z.ai/GLM, Kimi/Moonshot, OpenAI, or custom endpoint support.
   Source: `README.md:16`, `README.md:52-54`.
   Confidence: high.

4. CLI and messaging-platform behavior remain coherent across Telegram, Discord, Slack, WhatsApp, Signal, and CLI gateway surfaces.
   Source: `README.md:20`, `README.md:52-57`.
   Confidence: high.

5. The learning loop remains intact: memory nudges, autonomous skill creation, skill self-improvement, FTS5 session search, and Honcho integration must not regress when touching agent/session/skill code.
   Source: `README.md:14`, `README.md:21`.
   Confidence: high.

6. Output economy remains compact by default while preserving recovery evidence, and output-limit configuration must continue to flow across CLI, gateway, ACP/API-server, and Paperclip handoff.
   Source: `docs/output_contract.md:1-15`, `docs/output_contract.md:34-52`.
   Confidence: high.

7. Scheduled automation and parallel delegation remain first-class: cron delivery and isolated subagent/delegation behavior must keep working when scheduler, gateway, tool, or context code changes.
   Source: `README.md:22-23`.
   Confidence: high.

8. Safety boundaries remain strict: dependency ranges should stay intentionally bounded, tests must not call real provider APIs by default, and Portfolio-OS bundles must refuse destructive repository/filesystem actions and unsafe launch readiness.
   Source: `pyproject.toml:13-36`, `.github/workflows/tests.yml:38-42`, `docs/portfolio_os/adapter_contract.md:21-30`.
   Confidence: high.

9. Portfolio-OS/Paperclip adapter contracts remain stable: validate, dry-run, dispatch, status, and resume commands must preserve result artifacts that include run id, target repo, branch, commit, changed files, tests, QA status, blockers, next actions, Paperclip issue ids, and GStack pointers.
   Source: `docs/portfolio_os/adapter_contract.md:3-13`, `docs/portfolio_os/adapter_contract.md:32-40`.
   Confidence: medium.

10. Website/docs changes must satisfy the docs-site checks when that footprint is touched: diagram lint and Docusaurus build.
    Source: `.github/workflows/docs-site-checks.yml:33-39`.
    Confidence: high.

## Explicit Non-Goals

- Do not add native Windows support; the README directs Windows users to WSL2.
  Source: `README.md:36-38`.
  Confidence: high.

- Do not run integration tests or contact real inference providers unless a task explicitly requires that path.
  Source: `pyproject.toml:100-103`, `.github/workflows/tests.yml:38-42`.
  Confidence: high.

- Do not treat optional RL/Tinker-Atropos setup as required baseline verification.
  Source: `README.md:154`.
  Confidence: high.

- Do not perform object-level auditing, planning, coding, or fixes in Phase 0.
  Source: user-provided `Issue-Agnostic Improvement Loop v3`.
  Confidence: high.

- Do not assume the remote branch is clean/current; this checkout is currently `main...origin/main [ahead 2]`.
  Source: `git status --short --branch`.
  Confidence: high.

## Phase 0 Checkpoint

No low-confidence criteria currently block progress. Because `AUTONOMY=review`, Phase 1 should not start until the operator confirms this criteria file or provides corrections.
