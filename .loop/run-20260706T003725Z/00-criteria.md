# Phase 0 Criteria - Cross-Repo Factory Flywheel

Run: `20260706T003725Z`
Mode: `review`

## Vision

The system is a zero-touch autonomous software factory that converts Portfolio OS research and Internet Pipes evidence into Paperclip-governed company work, uses deterministic process adapters before model spend, invokes Hermes/local CLI lanes only when judgment or implementation is needed, verifies with GStack/QA/release receipts, and feeds compact learning back into Portfolio OS and Paperclip. A successful run produces cake: issue-bound, artifact-backed go-live progress toward valuable, profitable, marketable products, not only build runs, accepted patches, or PR ingredients.

Sources:
- Portfolio OS/Paperclip/gstack ownership split: `portfolio-os/docs/profit_flywheel_runbook.md:15-20`
- Paperclip orchestrator goals and projects: `portfolio-os/docs/profit_flywheel_runbook.md:51-78`
- Final-deliverable standard: `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:21-30`, `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:285-288`
- Go-live progress contract: `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:102-123`
- Operator clarification in this session: "ingredients are not the goal, the cake is."

## Health Criteria

| ID | Criterion | Evidence Source | Confidence |
| --- | --- | --- | --- |
| C1 | Every stage has an owner plane, trigger, minimal context, allowed tools, provider policy, receipt path, pass/fail rule, and token budget before model-bearing work runs. | `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:86-100` | High |
| C2 | Research and opportunity discovery cannot advance unless Codex/Paperclip/Hermes insights are written into a Portfolio OS artifact or Paperclip context-ledger receipt. | `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:137-151` | High |
| C3 | Existing-venture/duplicate/reskin paths stop or route before dossier, persona wake-up, new-company dispatch, or avoidable token spend. | `portfolio-os/docs/profit_flywheel_runbook.md:115-130`; `portfolio-os/docs/automations.md:104-115` | High |
| C4 | Council Chamber participates early enough to generate ranked venture hypotheses, child issues, and concrete Paperclip/Hermes execution tasks, with a score threshold and durable ledger. | `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:246-252` | High |
| C5 | Company success is measured as issue-bound, artifact-backed `goLiveDelta` and final deliverable units, not raw runs, patches, PRs, or quiet watch windows. | `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:102-123`; `paperclip/docs/guides/board-operator/unattended-factory-configuration.md:69-123` | High |
| C6 | Deterministic process adapters handle scriptable work before provider calls; Hermes/model lanes are reserved for implementation or judgment that deterministic runners cannot finish. | `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:47-63`, `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:274-288` | High |
| C7 | Hermes adapter runs are issue-keyed, bounded, final-response live, and record skill budget, tool-output budget, CLI capabilities, session params, and usage confidence. | `hermes-paperclip-adapter/README.md:7-37` | High |
| C8 | GStack provides POS evidence backfill, QA, patch planning, and bounded retrieval artifacts without mutating target repos. | `gstack/docs/portfolio_os_gstack_integration.md:1-81`; `gstack/docs/portfolio_os_retrieval_context.md:16-35` | High |
| C9 | ScrapeGraphAI, Graphify, GBrain, Repomix/context packs, and Internet Pipes are required station capabilities with executable receipts, not optional prompt suggestions. | `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:28-30`, `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:264-272` | High for requirement, Medium for current implementation completeness |
| C10 | Direct VOC, market behavior, competitive mechanics, pricing/willingness-to-pay proof, and recommendation artifacts gate council/dispatch spend. | `portfolio-os/docs/programs/voc_research.md:21-34`; `portfolio-os/docs/internet_pipes_factory_upgrade.md:79-104` | High |
| C11 | Context packs are used as map/delta/core indexes with freshness and profile recorded; large core packs require explicit justification or targeted rebuilds. | `.paperclip/.../context-packs/CONTEXT_ECONOMY.md:11-42`; `.paperclip/.../context-packs/latest.toon:1-8` | High |
| C12 | Provider lane routing chooses the cheapest capable lane with known quota/cache semantics and records providerLane/quota/cache metadata; provider capacity guards are not assumed current without fresh proof. | `paperclip/docs/guides/board-operator/flywheel-platform-coverage-plan.md:65-84`; `paperclip/docs/guides/board-operator/unattended-factory-configuration.md:125-151` | Medium because provider APIs can drift |
| C13 | System-owned blockers and self-heal waits do not become repeated agent work; natural cadence/fingerprint rules and heartbeat skips prevent token pinholes. | `paperclip/docs/guides/board-operator/token-spike-harness-pinhole-remediation.md:62-90` | High |
| C14 | Portfolio OS dirty generated artifacts are classified and preserved before any cleanup or regeneration; spent-token outputs are not discarded casually. | `portfolio-os/docs/automations.md:123-124`; live `portfolio-os` status observed 394 dirty paths | High |
| C15 | Live health claims must use fresh receipts. Current gaps include stale context packs and missing `latest-tokenomics-watch.json`. | `paperclip/docs/guides/board-operator/unattended-factory-configuration.md:62-80`; live Phase 0 checks | High |

## Non-Goals

- Do not collapse Portfolio OS into Paperclip or Paperclip into Hermes.
- Do not add a second recurring GStack scheduler.
- Do not spend provider tokens for Phase 0 discovery when local docs, receipts, dry-runs, and command surfaces suffice.
- Do not clean, move, or overwrite `portfolio-os` generated outputs before they are classified as valuable, stale, duplicate, or unsafe.
- Do not use context savings to starve real issue-bound build, research, QA, release, or learning work.

## Low-Confidence Items For Checkpoint

- Whether Phase 1 should refresh context packs before diagnosis or first diagnose why pack freshness enforcement did not fire.
- Whether the next live Paperclip DB pass should be strictly read-only or allowed to create a diagnostic issue if it finds missing station validators.
- Whether Graphify receipt validation should target existing graph exports first or immediately define a new graph schema contract.
