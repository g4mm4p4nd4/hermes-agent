# Phase 0 System Map

## End-To-End Flow

1. Portfolio OS discovers, scores, freezes, scaffolds, and dispatches opportunities.
2. Paperclip cockpit ingests Portfolio OS artifacts and turns them into company goals, issues, routines, approvals, context-ledger rows, and provider routing decisions.
3. Process adapters execute deterministic reconciliation, QA sweep, evidence backfill, release gate, and skill inventory work when a scriptable receipt can satisfy the issue.
4. Hermes and local CLI adapters handle model-bearing implementation, research synthesis, judgment, and issue-specific execution.
5. GStack, Graphify, ScrapeGraphAI, GBrain, Repomix, context packs, and Internet Pipes supply bounded evidence, graph intelligence, QA, retrieval, and learning artifacts.
6. Paperclip writes outcome, usage, work products, and context-ledger receipts; Portfolio OS ingests results back into reports, state, repo memory, and future source-quality priors.

## Planes And Contracts

| Stage | Owner Plane | Minimal Context | Required Receipt | Notes |
| --- | --- | --- | --- | --- |
| Research | Portfolio OS + Paperclip Signal Desk | Latest research batch, market/VOC files, Internet Pipes KB, targeted source receipts | Portfolio OS evidence rows, research report, issue-linked context-ledger row | Codex/OpenAI insights must be ingested before downstream Hermes work. |
| Evidence | Portfolio OS Evidence Custodian + ScrapeGraphAI/GBrain | Source URLs/docs, direct VOC, market/behavior/pricing proof, prior-learning lookup | Structured JSON extraction receipt, cited memory ids, normalized evidence candidates | ScrapeGraphAI and GBrain need executable validators. |
| Gate | Paperclip Council Chamber + Portfolio OS existing-venture gate | Venture ledger, company list, current evidence score, repo feasibility, competitive gap | Gate decision, child issues for distinct hypotheses, council hypothesis ledger | Duplicate/existing company should drop priority or route to existing venture. |
| Dispatch | Portfolio OS Truth Boundary + Paperclip process adapter | Frozen selection, selection snapshot, dispatch JSON, hashes | Immutable dispatch artifact, Paperclip issue contracts with hashes | Hash/source/issue mismatch blocks before provider calls. |
| Implementation | Process adapter first, Hermes second | Issue packet, map context pack, targeted files, Graphify map if broad source required | Changed files, tests, docs, Hermes result, usage/session metadata | Broad core packs need targeted rebuild if too large. |
| QA | Process runbook + GStack | Dispatch contract, target URL/surface, scaffold paths, Internet Pipes readiness | `qa_report.md`, screenshots, regression notes, issue done/blocked | No screenshot/report means no QA pass. |
| Release | Process adapter + ship-capable lane | Branch state, dirty paths, release gate command, approvals | Release report, approval state, hashes, issue closure or blocker | Model lane only after process gate proves residual work. |
| Learning | Paperclip + GBrain + Portfolio OS | Final work product, issue outcome, compact receipt | Work products, context ledger, source-quality priors, compact project memory | Next run gets pointers and digest, not transcript replay. |

## Current Runtime Findings

- Paperclip health endpoint is live and authenticated-private on `3100`; no `3101` listener observed.
- Context-pack manifest is stale by policy. It was generated at `2026-07-04T19:32:04.679Z` with `staleAfterHours: 24`, while this run is `2026-07-06T00:37:25Z`.
- Context-pack manifest disagrees with live repo state. Example: it records `paperclip` head `cac138283` and `dirty: 70`; live Phase 0 shows head `0924745043cb1e30ba8b0067b52b210234e11bb6` and clean.
- `latest-tokenomics-watch.json` is missing from cockpit ops data, so current token-reduction and valuable-output status cannot be asserted from the required watch artifact.
- `portfolio-os` is dirty with 394 paths, including repo memory, market signals, state, reports, skills, council runs, scaffolds, and VOC outputs. This is likely a mix of valuable generated outputs and stale/noisy artifacts; it must be classified before cleanup or regeneration.

## Immediate Phase 1 Shards

- Cockpit runtime and DB source of truth: routines, runs, context ledger, work products, company go-live contracts, active blockers.
- Portfolio OS artifact preservation and dirty-state classifier: separate valuable generated evidence from stale blockers and unrelated edits.
- Context economy and pack freshness: refresh policy enforcement, stale pack consumers, core-pack escalation rules.
- Adapter and provider routing: Hermes adapter, Gemini/Claude/Codex fallback metrics, MiniMax quota watch, final-response liveness.
- Station validator gap: ScrapeGraphAI, Graphify, GBrain, context-pack, and Internet Pipes receipt schemas.
- Cake metrics: final deliverable units, go-live deltas, issue closure, QA/release proofs, and stale ingredient-only work.
