# Phase 0 Repository And Runtime Inventory

Collected: `2026-07-06T00:37:25Z`

## Local Repositories

| Path | Branch / Head | Dirty State | Role |
| --- | --- | --- | --- |
| `/Users/mnm/Documents/Github/portfolio-os` | `main...origin/main [ahead 5]`, `9cefde0d5a0802aaf8b65cd5d4e808848380d82d` | 394 paths | Truth-plane artifacts, research, dispatch, Internet Pipes scoring. Preserve and classify. |
| `/Users/mnm/Documents/Github/paperclip` | `main...origin/main [ahead 32]`, `0924745043cb1e30ba8b0067b52b210234e11bb6` | clean | Cockpit code, routines, adapters, process runbooks, context ledger. |
| `/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit` | not a git repo | live runtime state | Paperclip data dir, DB, adapter plugins, receipts, context packs. |
| `/Users/mnm/Documents/Github/hermes-agent` | `main...origin/main [ahead 2]`, `f289cf97d63ae052dac5cce9ae785a58190da877` | `.loop/` untracked | Hermes CLI/model engine and current loop artifacts. |
| `/Users/mnm/Documents/Github/hermes-paperclip-adapter` | `main...origin/main [ahead 2]`, `8219b3ae0dd21d9ca68d822e5546be1cb8ed9746` | clean | External `hermes_local` adapter. |
| `/Users/mnm/Documents/Github/gstack` | `main...origin/main [ahead 1]`, `50c67adcadd9827ebccb07f1c1dcd3106120f018` | clean | Invoked-only skills, POS artifacts, QA, retrieval, GBrain sync. |
| `/Users/mnm/Documents/Github/ScrapeGraph` | `main...origin/main`, `cfb815fb0bba3dfc8262a24a7ddab28e22e13893` | clean | Upstream ScrapeGraphAI checkout. |
| `/Users/mnm/Documents/Github/internet-pipes-knowledgebase` | observed `main` earlier in Phase 0 | untracked `reports/` observed earlier | Internet Pipes KB and Notion loaders. |
| `/Users/mnm/Documents/Github/hermes-agent-upstream-cutover` | `codex/hermes-upstream-paperclip-cutover...upstream/main` | dirty | Auxiliary prior cutover worktree, not primary runtime. |

## Installed Commands

| Command | Path | Phase 0 Result |
| --- | --- | --- |
| `graphify` | `/Users/mnm/.local/bin/graphify` | Help works; repo checkout not present at `/Users/mnm/Documents/Github/graphify`. |
| `scrapegraphai` | `/Users/mnm/.local/bin/scrapegraphai` | Help and dry-run work. |
| `codex-scrapegraph` | `/Users/mnm/.local/bin/codex-scrapegraph` | Help works. |
| `pnpm` | `/Users/mnm/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/pnpm` | Used for Paperclip baselines. |
| `uv` | `/Users/mnm/.local/bin/uv` | Available; Internet Pipes tests not run in this pass. |
| `gbrain` | not found in PATH | GBrain capability is documented through GStack, but executable availability was not confirmed. |

## Cockpit Runtime

- Health endpoint: `http://127.0.0.1:3100/api/health`
- Health result: `{"status":"ok","version":"0.3.1","deploymentMode":"authenticated","deploymentExposure":"private","authReady":true,...}`
- Listener: `node` on `*:3100`; no `3101` listener observed.
- Latest guard receipt: `instances/default/data/ops/paperclip-guard/latest.json`, status `healthy`, finished `2026-07-05T20:04:47.953617+00:00`.
- Context packs: generated `2026-07-04T19:32:04.679Z`, stale after 24 hours.
- Tokenomics watch: `instances/default/data/ops/latest-tokenomics-watch.json` missing.

## Context Pack Mismatch

The current context-pack manifest is useful as an inventory but not authoritative for live state:

- It records `paperclip` head `cac138283` and `dirty: 70`; live repo is `092474504...` and clean.
- It records `hermes-agent` head `6be74cea` and `dirty: 9`; live repo is `f289cf97...` with only `.loop/` untracked.
- It records `gstack` head `72e936a8` and `dirty: 5`; live repo is `50c67adc...` and clean.

Phase 1 should either refresh map/delta packs first or treat all pack metadata as stale until refreshed.
