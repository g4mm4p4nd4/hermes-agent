# Phase 0 Checkpoint Questions

The loop is in `review` mode, so Phase 1 should wait for confirmation. These questions are scoped to decisions that materially affect safety, token cost, or live-state mutation.

## Q1 - Context Pack Refresh

What was found:
- Context packs were generated at `2026-07-04T19:32:04.679Z` with `staleAfterHours: 24`.
- They disagree with live repo state for `paperclip`, `hermes-agent`, and `gstack`.

Ambiguity:
- Should Phase 1 refresh map/delta packs before diagnosis, or first diagnose why pack freshness enforcement let stale packs remain?

Options:
- Refresh map/delta first (recommended): gives workers accurate bounded context and records freshness as the first repair target. Slightly mutates cockpit ops artifacts.
- Diagnose stale-pack enforcement first: strictly read-only, but every worker must ignore stale pack metadata and do more direct file reads.
- Refresh all profiles: most complete, but core packs are expensive and violate the current context economy default unless justified.

Default if unanswered:
- Refresh map/delta only for `portfolio-os`, `paperclip`, `hermes-agent`, `hermes-paperclip-adapter`, and `gstack` before model-bearing Phase 1 workers.

## Q2 - Portfolio OS Dirty Artifact Handling

What was found:
- `portfolio-os` has 394 dirty paths spanning repo memory, market signals, reports, skills, state, council runs, scaffolds, and VOC outputs.

Ambiguity:
- Should Phase 1 classify dirty artifacts read-only first, or may it commit/preserve obvious generated output batches as part of stabilization?

Options:
- Read-only classify first (recommended): avoids losing or mis-bundling spent-token output; slower to clean.
- Commit obvious batches immediately: protects data sooner, but risks mixing unrelated live output.
- Ignore dirty state for now: fastest diagnosis, but unsafe for truth-plane commands and may hide stale blockers.

Default if unanswered:
- Read-only classify first and produce a commit plan without changing `portfolio-os`.

## Q3 - Live Paperclip DB Access

What was found:
- Paperclip server is healthy and authenticated-private.
- Prior memory and docs say live company execution reporting must query DB/runtime state rather than repo diffs.

Ambiguity:
- Should Phase 1 inspect live embedded Postgres and context-ledger tables directly?

Options:
- Read-only DB queries (recommended): necessary to diagnose routines, work products, context ledger, and cake metrics.
- API-only reads: safer surface, but board-auth endpoints may hide data and miss ledger details.
- No live reads: safest, but cannot prove current factory operation.

Default if unanswered:
- Use read-only DB/API queries and write no runtime state.

## Q4 - Graphify/GBrain Validator Target

What was found:
- Paperclip coverage plan explicitly calls for executable validators for ScrapeGraphAI, Graphify, and GBrain receipt schemas.
- `graphify` command exists; `gbrain` was not found on PATH.

Ambiguity:
- Should Phase 1 design validators around current installed commands, desired station contract, or both?

Options:
- Both contract and installed-command reality (recommended): exposes missing executable paths without blocking schema design.
- Installed commands only: practical, but may under-spec GBrain and future station needs.
- Desired contract only: clean architecture, but risks ignoring local runtime gaps.

Default if unanswered:
- Build findings around both the desired receipt schema and the current command availability.
