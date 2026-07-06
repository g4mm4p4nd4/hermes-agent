# Autonomous Software Factory Loop Project Map

Last refreshed: `2026-07-06T00:37:25Z`
Latest run: `.loop/run-20260706T003725Z/`
Supersedes Hermes-only run: `.loop/run-20260706T000316Z/`

## Scope

This loop is not a single-repo Hermes improvement pass. It covers the complete
local factory path:

`portfolio-os research -> Paperclip cockpit governance -> Paperclip adapters -> Hermes/local CLI execution -> GStack/Graphify/ScrapeGraphAI/GBrain/context-pack evidence -> Portfolio OS/Paperclip receipts`

The durable goal is not more runs, patches, or PRs. The goal is issue-bound,
artifact-backed, go-live progress for revenue-capable companies and products.

## Authority Repositories And Runtime Roots

| Plane | Path | Role |
| --- | --- | --- |
| Portfolio OS | `/Users/mnm/Documents/Github/portfolio-os` | Truth plane for research, evidence, frozen selections, execution scaffolds, dispatch artifacts, and Internet Pipes readiness. |
| Paperclip | `/Users/mnm/Documents/Github/paperclip` | Cockpit source for companies, issues, routines, adapters, provider routing, process runbooks, context ledger, and work products. |
| Paperclip cockpit state | `/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit` | Live runtime data, embedded Postgres, adapter plugins, guard receipts, context packs, and ops receipts. |
| Hermes Agent | `/Users/mnm/Documents/Github/hermes-agent` | Local model-bearing implementation engine and CLI invoked by the Hermes adapter. |
| Hermes Paperclip Adapter | `/Users/mnm/Documents/Github/hermes-paperclip-adapter` | External `hermes_local` adapter that launches Hermes, bounds context, accounts usage, and recovers final responses. |
| GStack | `/Users/mnm/Documents/Github/gstack` | Invoked-only specialist workflow layer for QA, evidence backfill, patch planning, retrieval context, review, ship, and browser-assisted validation. |
| Graphify | `/Users/mnm/.local/bin/graphify` plus graph outputs | Repo/dependency graph intelligence. No `/Users/mnm/Documents/Github/graphify` checkout was present during Phase 0. |
| ScrapeGraphAI | `/Users/mnm/.local/bin/scrapegraphai`, `/Users/mnm/.codex/tools/scrapegraphai`, `/Users/mnm/Documents/Github/ScrapeGraph` | Structured extraction lane for external/source-backed evidence receipts. |
| Internet Pipes KB | `/Users/mnm/Documents/Github/internet-pipes-knowledgebase` | Local source-backed operating manual and graph-ready evidence corpus for research, validation, evaluation, differentiation, visualization, and recommendation workflows. |

## Verified Current State

- `paperclip`: `main`, head `0924745043cb1e30ba8b0067b52b210234e11bb6`, `main...origin/main [ahead 32]`, clean.
- `hermes-agent`: `main`, head `f289cf97d63ae052dac5cce9ae785a58190da877`, `main...origin/main [ahead 2]`, only `.loop/` untracked from this loop.
- `hermes-paperclip-adapter`: `main`, head `8219b3ae0dd21d9ca68d822e5546be1cb8ed9746`, `main...origin/main [ahead 2]`, clean.
- `gstack`: `main`, head `50c67adcadd9827ebccb07f1c1dcd3106120f018`, `main...origin/main [ahead 1]`, clean.
- `ScrapeGraph`: `main`, head `cfb815fb0bba3dfc8262a24a7ddab28e22e13893`, clean.
- `portfolio-os`: `main`, head `9cefde0d5a0802aaf8b65cd5d4e808848380d82d`, `main...origin/main [ahead 5]`, dirty with 394 tracked/untracked generated research, repo-memory, skill, report, and scaffold artifacts. Treat as valuable live artifact state until classified, not cleanup noise.
- Cockpit health: `curl http://127.0.0.1:3100/api/health` returned `status=ok`, `version=0.3.1`, authenticated private mode. `3100` has the Paperclip server listener; `3101` had no listener.

## Source Contracts

- Portfolio OS owns truth-plane artifacts and Paperclip owns persistent venture discovery; GStack is invoked-only, not a scheduler: `portfolio-os/docs/profit_flywheel_runbook.md:15-20`.
- The Portfolio OS Orchestrator owns Signal Desk, Council Chamber, Asset Composition Lab, Venture Graduation, and Truth Boundary work: `portfolio-os/docs/profit_flywheel_runbook.md:51-78`.
- Twice-daily Paperclip routine order and gate outcomes are explicit: `portfolio-os/docs/profit_flywheel_runbook.md:100-130`.
- Paperclip's platform coverage plan says the missing layer is station ownership, required receipts, required tools, and lane policy: `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:5-45`.
- "Success" is go-live progress and final deliverables with receipts, not generic completed turns: `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:102-123` and `paperclip/docs/guides/board-operator/unattended-factory-configuration.md:69-123`.
- Hermes adapter must bound skills, context, tool output, session identity, final response liveness, and provider fallback: `hermes-paperclip-adapter/README.md:7-37` and `hermes-paperclip-adapter/README.md:51-62`.
- GStack emits artifacts and does not mutate target repos in the POS flow: `gstack/docs/portfolio_os_gstack_integration.md:1-81`.
- Internet Pipes KB is a local source-backed operating manual with JSONL, SQLite, and Graphify exports: `internet-pipes-knowledgebase/README.md:1-30`.
- Context packs are stale after 24 hours and map packs are the default entry point: `.paperclip/.../context-packs/latest.toon:1-8` and `.paperclip/.../context-packs/CONTEXT_ECONOMY.md:11-42`.

## Command Baselines

Current Phase 0 command results are recorded in `.loop/run-20260706T003725Z/00-commands.md`.

Earlier Hermes-only baseline retained:

```bash
source venv/bin/activate && OPENROUTER_API_KEY="" OPENAI_API_KEY="" NOUS_API_KEY="" python -m pytest tests/ -q --ignore=tests/integration --tb=short -n auto
```

Result: `6351 passed, 164 skipped, 110 warnings in 65.87s`.

## Standing Constraints

- Preserve `portfolio-os` dirty artifact state until classified; it includes generated research/output that may represent already-spent tokens.
- Do not reintroduce Paperclip-owned routines as repo-scoped Portfolio OS automations.
- Do not run full Graphify over large repos without narrowing; use context packs, existing graph outputs, or targeted graph generation first.
- Do not spend ScrapeGraphAI/model quota in discovery; use dry-run or existing local KB unless a later phase has an evidence extraction work item.
- Refresh context packs before model-bearing broad diagnosis because current pack metadata is stale and disagrees with live repo state.
- Treat missing `latest-tokenomics-watch.json` as an operational evidence gap.

## Loop Defaults

- `N_PLANS=5`
- `MAX_LOOPS=2`
- `SEVERITY_FLOOR=High`
- `AUTONOMY=review`

## Current Checkpoint

Corrected cross-repo Phase 0 completed. Await operator confirmation of `.loop/run-20260706T003725Z/00-criteria.md` and checkpoint defaults before Phase 1 diagnosis.
