# Phase 1 Diagnosis

Phase: 1
Status: initial fixes applied, larger runtime fixes still open

## P1-001: Venture Context Packs Were Outside Canary Coverage

Severity: High
Status: fixed in code, pending Paperclip restart/deploy

Evidence:

- The live YT-Synth CMO run `99bb0ff0-c1a7-4fba-9163-bb5d078f3471` used stale context-economy metadata before the venture refresh pass.
- `server/src/services/context-economy-live-canary.ts` only targeted `paperclip`, `hermes-agent`, `portfolio-os`, and `gstack`.
- The context-pack manifest includes active venture slugs `leadforge`, `yt-synth`, and `agency-swarm`.

Fix applied:

- Added `leadforge`, `yt-synth`, and `agency-swarm` to `CONTEXT_ECONOMY_CANARY_TARGETS`.
- Added tests proving the default target list includes infrastructure and venture repos.
- Added tests proving venture canaries are validated against their own repo slugs.

Verification:

```bash
pnpm --filter @paperclipai/server exec vitest run src/__tests__/context-economy-live-canary.test.ts src/__tests__/heartbeat-context-economy.test.ts --testTimeout=15000
pnpm --filter @paperclipai/server typecheck
```

Result: both passed.

Operational status:

- Paperclip was restarted after the fix.
- The duplicate 3100/3101 server state created by the first restart attempt was corrected.
- The active server is healthy on port 3100 and the loaded canary target list includes `leadforge`, `yt-synth`, and `agency-swarm`.

## P1-002: Blocked Timer Refreshes Can Burn Large Tokens Without Cake

Severity: Critical
Status: open

Evidence:

- YT-Synth CMO run consumed 81,329 input tokens, 10,855 output tokens, and 1,011,712 cached input tokens.
- The run completed technically but ended blocked by the same external credential and warm-up constraints.
- Output did not produce a launched channel post, deployment, customer signal, revenue artifact, or other cake metric.

Required fix:

- Add blocker fingerprinting at scheduler/runtime boundaries.
- If an issue is already blocked with the same fingerprint and no new external signal has arrived, skip full Hermes execution and record a bounded no-op receipt.
- Only rerun full Hermes when the blocker fingerprint changes, a credential becomes available, a provider quota recovers, or a human/board comment changes the state.

## P1-003: Context Economy Hints Report Stale State But Do Not Fail Closed

Severity: High
Status: partially fixed by wider canary coverage, runtime guard still open

Evidence:

- `buildPaperclipContextEconomyHint()` computes `freshnessStatus`, but live dispatch can still include stale hint data.
- Existing canaries can catch staleness only for target repos they know about.

Required fix:

- Gate live dispatch when context packs are stale, missing, or head-mismatched for the repo being used.
- Prefer pre-dispatch refresh of map/delta packs where safe.
- If refresh is unavailable or fails, run a minimal no-pack prompt rather than injecting stale pack provenance.

## P1-004: Portfolio OS Artifact Value Was At Risk In Dirty State

Severity: High
Status: fixed for obvious batches

Evidence:

- Portfolio OS had uncommitted skill-curator and flywheel artifact output.
- Repeated prior memory notes show POS daily artifacts had been blocked by auth and dirty planes.

Fix applied:

- Committed `8fc4c50ad3 Preserve skill curator annotations`.
- Committed `2b7080a741 Preserve July 5 flywheel artifacts`.
- Validated skill curator output, JSON syntax, and staged secret scan before commit.

Remaining:

- Untracked local helper scripts remain intentionally uncommitted until generalized or discarded.

## P1-005: Graphify and GBrain Exist But Are Not Yet Production Receipt Gates

Severity: High
Status: installed-command reality fixed, integration open

Evidence:

- Graphify CLI works and existing Paperclip graph queries work.
- GBrain was missing before this run and is now installed on local PGLite.
- GBrain doctor passes detector checks but warns because the brain is empty and lacks embeddings/link coverage.

Required fix:

- Add a Paperclip/Hermes receipt schema for Graphify, GBrain, and ScrapeGraphAI command reality.
- Require these receipts in research and council routines before spending large-model tokens.
- Store compact evidence fingerprints, not raw replay context.

## P1-006: Company Agent State Still Blocks Cake Output

Severity: High
Status: open

Evidence:

- LeadForge QA is in `error`.
- agency-swarm has most execution agents paused and Skill Curator terminated.
- Portfolio OS Orchestrator has terminated core agents.
- YT-Synth had a technically successful CMO run that still ended blocked.

Required fix:

- Add a scheduler/runtime self-heal pass for paused, terminated, and errored agents based on company goal criticality.
- Separate intentional pauses from bad configuration.
- Re-enable or recreate missing execution agents when a company has open go-live gaps.

## P1-007: Adapter and Auxiliary Repos Are Not First-Class In Context Packs

Severity: Medium
Status: open

Evidence:

- The context-pack builder lacks configured slugs for `hermes-paperclip-adapter`, Graphify, ScrapeGraphAI, and GBrain even though they are part of the factory loop.

Required fix:

- Add configured context-pack inventory entries or explicit receipt substitutes for these repos/tools.
- Avoid injecting their full code into every task. Use map/delta and command-reality receipts unless implementation work in that repo is required.

## P1-008: Incremental Comment Fetches Could 500 During Heartbeats

Severity: High
Status: fixed in code, pending Paperclip restart/deploy

Evidence:

- Runtime log `/tmp/paperclip-screen-fallback.log` showed `GET /api/issues/:id/comments?after=<comment-id>&order=asc` returning 500.
- The driver error was `Received an instance of Date` while binding the anchor timestamp in a raw SQL cursor comparison.
- This blocks comment-driven wake context and can cause agents to miss the newest human or agent comments.

Fix applied:

- Commit `61b9fdae9 fix(issues): normalize comment cursor timestamps`.
- Added `issueCommentCursorTimestamp()` to normalize Date anchors before raw SQL binding.
- Added an embedded Postgres regression test for ascending and descending cursor pagination.

Verification:

```bash
pnpm --filter @paperclipai/server exec vitest run src/__tests__/context-economy-live-canary.test.ts src/__tests__/heartbeat-context-economy.test.ts src/__tests__/issues-service.test.ts --testTimeout=30000
pnpm --filter @paperclipai/server typecheck
```

Result: both passed.

Operational status:

- Paperclip was restarted after the fix.
- The active server is healthy on port 3100.
- Post-restart source import confirms the server code contains the updated comment cursor implementation.

## Next Implementation Order

1. Force a context-economy canary ensure against all seven targets and verify no stale venture pack can pass silently.
2. Validate incremental comment fetches after restart by hitting the affected comments endpoint through the authenticated UI/API path.
3. Implement blocker fingerprint no-op suppression for repeated credential, quota, and warm-up blockers.
4. Add Graphify/GBrain/ScrapeGraphAI validator receipts to the research and council routines.
5. Repair paused, terminated, and errored company agents with self-heal rules tied to company go-live gaps.
