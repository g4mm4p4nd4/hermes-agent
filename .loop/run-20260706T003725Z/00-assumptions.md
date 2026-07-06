# Phase 0 Assumptions And Inferences

## Corrections From Prior Phase 0

- The earlier `.loop/run-20260706T000316Z/` pass was too narrow because it treated `hermes-agent` as the main project. It remains useful for the Hermes full-suite baseline, but it is superseded for system diagnosis by this cross-repo run.
- The correct unit of work is the flywheel, not the Hermes repo. Phase 1 should diagnose cross-plane failures even when the fix lands in only one repo.

## Safety Assumptions

- `portfolio-os` dirty output may contain valuable generated work from prior live runs. It should be preserved and classified before cleanup, regeneration, or commits.
- `paperclip`, `hermes-paperclip-adapter`, `gstack`, and `ScrapeGraph` are clean after Phase 0 command baselines.
- `.loop/` in `hermes-agent` is intentional new discovery output.

## Context Economy Assumptions

- Current context packs are stale and cannot be used as current-state evidence without refresh. They are still useful as a compact index of the intended pack policy and prior known repos.
- The stale pack metadata itself is a finding: if agents rely on it without freshness checks, they can reason from wrong heads and dirty-state claims.
- Full core packs are not default context. Map first, then targeted `rg`/file reads, then delta/core only with justification.

## Tooling Assumptions

- Graphify is available as an installed command, but the source checkout is not present at `/Users/mnm/Documents/Github/graphify`. Existing graph outputs and targeted `graphify query` should be preferred until a source repo is identified or installed.
- ScrapeGraphAI is available through local wrapper commands and can produce dry-run receipts without spending model quota. Live extraction should be tied to a specific evidence work item.
- `gbrain` was not found on PATH. GBrain remains part of the desired station contract through GStack docs, but executable validation is a Phase 1 finding.

## Operational Assumptions

- Paperclip health is necessary but not sufficient. A healthy dashboard does not prove the factory is operational; fresh canary, tokenomics watch, context-ledger, work-product, QA, and release receipts are required.
- Missing `latest-tokenomics-watch.json` means current token-reduction and valuable-output status cannot be claimed from the required watch artifact.
- The missing executable validators for ScrapeGraphAI, Graphify, and GBrain are a likely cross-plane gap because the Paperclip coverage plan lists them as follow-on hardening work.

## Defaults If Unanswered

- Phase 1 will remain read-only against live DB/runtime state unless a fix is explicitly in-scope.
- Phase 1 will refresh only map/delta context packs if needed for diagnosis; core packs require explicit justification.
- Phase 1 will treat `portfolio-os` dirty files as evidence to classify, not as clutter to remove.
