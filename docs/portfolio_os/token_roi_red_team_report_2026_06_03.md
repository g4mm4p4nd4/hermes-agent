# Token ROI Red-Team Report: Hermes, Paperclip, GStack, and Portfolio OS

Date: 2026-06-03

Scope:

- `hermes-agent`
- `hermes-paperclip-adapter`
- `paperclip`
- `portfolio-os`
- `gstack`
- Optional later lanes: Repomix, GBrain, Graphify, local vector retrieval

This was a read-heavy adversarial pass. The goal was to test whether the proposed architecture actually attacks the high-cost path for an unattended token and inference optimized agentic software and company factory.

## Executive Verdict

The proposed direction is correct, but the highest-value framing is sharper than "compress earlier":

1. Token replay bloat and storage/log bloat are different problems. Treating them as one problem hides where the rubber meets the road.
2. Hermes replay is the direct token-risk center. Paperclip can trigger Hermes resumes, but Hermes owns historical message materialization and should stop replaying old full tool outputs by default.
3. The Paperclip Hermes adapter is not currently the million-token culprit by itself for ordinary runs. It caps context at 16,000 chars and strips many noisy keys. Its bug is architectural: resumed sessions still get a freshly rendered full prompt instead of a compact resume delta, and it lacks prompt classes, component hashes, and enforceable budgets.
4. Paperclip lacks a first-class context ledger. It has rich run rows, run events, cost events, logs, and session state, but no normalized ledger that can answer "what components were injected, why, under which budget, with which hashes, and what cursor state was consumed?"
5. Portfolio OS context packs are the right deterministic evidence substrate. The policy already says use compact indexes and map packs first. The missing piece is runtime enforcement and telemetry, not another big retrieval system.
6. GBrain, Graphify, vectors, and local retrieval are useful later. They should not be the first fix for heartbeat/resume prompt bloat. Use them only after ledger events, pack provenance, and prompt budgets exist.

The permanent solve is:

```text
ledger-first resumes
+ prompt-class budgets
+ artifact-backed Hermes tool replay
+ content-addressed prompt blocks
+ context-pack manifest enforcement
+ compact run-log storage
+ optional retrieval over ledger artifacts after provenance exists
```

## Delegated Agent Findings

Six fresh GPT-5.5 xhigh agents were spawned for independent red-team lanes and their findings were synthesized here:

| Agent | Lane | Result |
| --- | --- | --- |
| Noether | Hermes storage and replay | Validated Hermes replay/materialization as direct token-risk center. Recommended schema v7 for artifacts, prompt blocks, replay content, and FTS-compatible search content. Ran focused Hermes tests: 222 passed. |
| Banach | Hermes Paperclip adapter | Confirmed full prompt is rebuilt even on resume. Found `passSessionId` schema/default mismatch. Ran adapter tests: 19 passed. |
| Russell | Paperclip ledger | Confirmed Paperclip has run/session/cost/log primitives but no normalized context ledger. Recommended ledger entries, components, cursors, and hard budget boundaries. |
| Kant | Portfolio OS context packs | Confirmed Repomix packs are the correct deterministic pack layer, but current packs were stale by policy and runtime routing does not enforce map-first behavior. |
| Avicenna | GStack, GBrain, Graphify, retrieval | Confirmed GStack has deterministic POS artifact helpers and optional GBrain sync hooks. Recommended retrieval only after ledger and pack provenance are structured. |
| Euler | Economics and instrumentation | Refuted the adapter-only million-token explanation for normal runs. Identified Hermes replay as direct token risk and Paperclip run-log streaming snapshots as a major storage ROI target. |

## Validated Metrics

### Hermes SQLite State

Source: local `~/.hermes/state.db`, filtered where relevant to Paperclip sessions.

| Area | Validated value |
| --- | ---: |
| Paperclip sessions | 1,207 |
| Paperclip session system-prompt chars | 35,893,205 |
| Paperclip messages | 14,911 rows |
| Paperclip message content chars | 32,337,285 |
| Paperclip user message chars | 12,636,883 |
| Paperclip tool message chars | 19,111,907 |
| Paperclip assistant message chars | 588,495 |
| User exact duplicate rows | 43 / 1,596, 2.69% |
| User normalized duplicate rows | 920 / 1,596, 57.64% |
| Repeated normalized user-line waste estimate | 11,019,443 chars, 88.11% |
| All session system prompt chars | 650,779,500 |
| Exact system-prompt duplicate rows | 15,795 / 23,634 |
| Exact system-prompt dedupe savings | 433,836,588 chars |
| Hermes state DB size | 1.0G |
| `sessions` table size | 676,794,368 bytes |
| `messages` table size | 342,151,168 bytes |
| `messages_fts_data` size | 60,039,168 bytes |

The earlier prompt's "95.76% repeated prompt-line waste" was not exactly reproduced with the local normalization used in this pass. The reproduced number was lower but still decisive: 88.11% repeated normalized line waste.

### Hermes Tool Replay Savings

Hypothetical cap applied to historical Paperclip tool messages:

| Tool message cap | Chars saved | Rough tokens saved |
| --- | ---: | ---: |
| 2,000 chars | 12,172,809 | 3,043,202 |
| 4,000 chars | 8,873,077 | 2,218,269 |
| 8,000 chars | 5,736,350 | 1,434,087 |
| 12,000 chars | 4,358,956 | 1,089,739 |

This supports artifact-backed replay. Old large tool results should remain exact and searchable as artifacts, but replay should default to bounded summaries and pointers.

### Largest Paperclip Hermes Replay Sessions

Top Paperclip sessions by stored message chars:

| Session | Message rows | Stored chars | Rough tokens |
| --- | ---: | ---: | ---: |
| `20260601_065614_38f35c` | 267 | 1,254,961 | 313,740 |
| `20260601_065321_9e21ad` | 400 | 1,208,706 | 302,176 |
| `20260601_074043_b8c3b9` | 246 | 1,160,023 | 290,005 |

These are not theoretical. A single resumed Hermes session can carry hundreds of thousands of rough tokens of replayable content if materialized naively.

### Paperclip Run Logs

Source: local Paperclip cockpit data directory.

| Area | Validated value |
| --- | ---: |
| Run-log directory size | 4.0G |
| NDJSON files | 6,671 |
| Largest NDJSON log | 91,946,802 bytes |
| Next largest logs | 87,093,724 and 85,413,617 bytes |

The run-log store appends streamed JSONL chunks and finalizes bytes/hash. Reads default to a 256,000 byte cap, so this is primarily storage and UX risk, not direct prompt replay by default. It is still a major ROI target because repeated streaming assistant snapshots are expensive to store, inspect, sync, and audit.

### Repomix Context Packs

Validated from the current context-pack index.

| Repo/profile | Estimated tokens |
| --- | ---: |
| `paperclip` core | 3,045,841 |
| `portfolio-os` core | 1,738,228 |
| `hermes-agent` core | 806,257 |
| `portfolio-os` map | 6,798 |
| `portfolio-os` delta | 128,897 |

The core packs are too large to be default runtime context. Map packs and compact indexes are the only sane default. Core packs should require explicit profile escalation and budget attribution.

Important freshness finding: the context-pack index was stale by its own policy during this pass. The live clock was 2026-06-03T01:46:46Z, while the manifest was generated 2026-06-01T04:20:42.958Z, and the `portfolio-os` repo entry was generated 2026-05-31T05:17:52.051Z.

## Red-Team Conclusions

### Assumption: "Compress earlier" is the main fix

Verdict: incomplete.

Hermes already has reactive context compression. The bigger architectural issue is that raw historical messages are the default replay substrate. Compression after the transcript has already been assembled is too late and too nondeterministic.

Permanent fix:

- Store exact raw transcript for audit.
- Store exact large tool outputs as artifacts.
- Store searchable `search_content`.
- Replay bounded `replay_content`.
- Preserve exact current turn, last relevant tool-call group, latest status/final, decisive errors, todos, hashes, paths, and exit codes.

### Assumption: Paperclip Hermes adapter is the main million-token source

Verdict: partly refuted.

The adapter has real problems, but ordinary prompt construction is capped:

- Default context cap: 16,000 chars.
- Default JSON string cap: 2,000 chars.
- Noisy keys such as logs, tool results, raw transcript, vectors, embeddings, screenshots, stdout, and stderr are omitted.

The adapter still needs prompt classes because it currently renders a full prompt on every execution, including resumed runs. The issue is repeatable waste and weak accounting more than direct million-token prompt injection from this layer alone.

### Assumption: Exact duplicate hashing is enough

Verdict: false.

Exact duplicate user prompts were only 2.69%. Normalized duplicates and repeated prompt-line waste were massive. Timestamps, run IDs, receipt paths, comment IDs, and status wrappers defeat exact hashing.

Permanent fix:

- Component-level fingerprints.
- Stable block hashes for role text, policy text, context manifest, instructions, task payload, wake event, comment payload, and repo pack references.
- Normalize volatile fields before dedupe.
- Keep raw prompt text for audit, but dedupe replay/materialization by components.

### Assumption: Repomix should be the evidence index

Verdict: correct, with enforcement gaps.

Repomix is already deterministic, hashable, and cheap at the map/index layer. It should be promoted into runtime telemetry and routing:

- Manifest path.
- Repo slug.
- Profile used.
- Pack SHA.
- Pack HEAD.
- Current checkout HEAD.
- Dirty count.
- Freshness status.
- Estimated tokens.
- Budget class.

No system should paste core packs by default.

### Assumption: Graphify should be used now

Verdict: not as the first fix.

Graphify is useful for relationship queries after structured ledger events exist. It is not the right primary fix for repeated heartbeat or resume prompt bloat.

Use later for:

- Repo dependency and import relationships.
- Ownership and bus-factor graph queries.
- Cross-run issue/task/agent lineage.
- Retrieval explanations tied to pack SHA and HEAD.

Do not use it to paper over missing prompt budgets, missing ledger entries, or raw transcript replay.

## Target Architecture

### Prompt Classes

| Prompt class | Purpose | Budget target |
| --- | --- | ---: |
| `bootstrap` | Full role, durable instructions, initial task, context manifest | One per task session |
| `resume_delta` | Event-only resume with cursor and decisive state | <= 2,000 tokens |
| `timer_delta` | Tiny heartbeat/check-in prompt | <= 2,000 tokens, preferably far lower |
| `comment_delta` | Current comment/event payload | <= 3,000 tokens |
| `context_manifest` | Paths, hashes, pack refs, freshness, not pasted repo context | <= 1,000 tokens |
| `recovery_delta` | Bounded failure/test/receipt recovery payload | <= 4,000 tokens unless explicitly escalated |

### Context Ledger

Paperclip should persist a ledger entry per run prompt materialization:

- Company, run, agent, issue, task key, project, cwd, branch.
- Prompt class.
- Prompt fingerprint and algorithm version.
- Adapter type and adapter version.
- Model/provider.
- Template version.
- Component list with hashes, chars, rough tokens, source IDs, and truncation status.
- Session ID before/after.
- Wake/comment/task cursors.
- Context pack refs and freshness.
- Budget policy version.
- Estimated prompt tokens.
- Actual provider token usage when available.
- Cached input tokens when available.
- Final outcome, blocker, receipt paths, and status transition.

This ledger should be queryable by run, issue, task key, agent, and pack SHA.

### Hermes Artifact-Backed Replay

Hermes should add a storage layer near `hermes_state.py`:

- `artifacts`: content-addressed exact blobs, inline or file-backed.
- `message_artifacts`: links messages to artifacts by field and replay policy.
- `messages.replay_content`: deterministic bounded replay material.
- `messages.search_content`: FTS-compatible search material.
- `messages.content_sha256`.
- `messages.content_is_artifact_backed`.
- `prompt_blocks`: content-addressed stable prompt blocks.
- `session_prompt_blocks`: ordered block references per session.

Compatibility rule:

Keep exact `sessions.system_prompt` until byte-identical reconstruction and prompt-cache safety are proven. Do not break prompt caching by rewriting historical system prompts in active sessions.

### Replay Policy

Replay exactly by default:

- Current turn.
- Last complete tool-call group if still relevant.
- Latest assistant final/status for the active task.
- Recent decisive failures.
- Test output summaries and exact exit codes.
- Receipt paths, hashes, run IDs, branch names, and changed-file lists.
- Current todo state.

Replay as ledger summaries:

- Wake events keyed by source, task ID, issue ID, comment ID, agent ID, cwd, branch.
- First/last seen, count, transition, final outcome, blocker, receipt path.
- Context pack manifest hash, pack SHA, prompt class, budget version.

Archive but do not replay by default:

- Old terminal logs.
- Large file reads.
- Patch diffs after extracting changed files/status.
- Skill docs.
- Repeated scheduler wakes.
- Empty assistant tool-call carriers.
- Old reasoning traces.

## Repo Ownership and Implementation Order

### 1. `hermes-paperclip-adapter`: prompt classes and metrics

Implement first because it is small, high-leverage, and creates downstream telemetry.

Required changes:

- Add prompt class selection: `bootstrap`, `resume_delta`, `resume_refresh`, `timer_delta`, `comment_delta`.
- On valid resume, send `resume_delta` rather than the full template/context payload.
- Add component hashes and char/token metrics for template, instructions, context, wake payload, comment payload, and manifest.
- Fix `passSessionId` so the schema default of true is the runtime default.
- Cap optional instruction files and emit truncation flags.
- Persist prompt/session metadata in the session codec.
- Emit telemetry: `promptClass`, `resumeMode`, `estimatedPromptTokens`, component totals, duplicate indicators, budget version, pack usage, truncation flags, and `passSessionIdEffective`.

Tests:

- Resume delta omits full template when hashes match.
- Resume refresh occurs when stable component hashes change.
- `passSessionId` defaults to true.
- Budget enforcement truncates or fails closed by class.
- Session codec round-trips prompt metadata.
- Fenced context cannot inject new instructions.
- Existing `npm test` remains green.

### 2. `paperclip`: context ledger and budget enforcement

Implement second because it makes prompt classes enforceable and auditable.

Required changes:

- Add `context_ledger_entries`.
- Add `context_ledger_components`.
- Add `agent_context_cursors`.
- Add prompt-budget policy config by adapter and prompt class.
- Enforce budgets pre-queue, pre-claim, and immediately before adapter execution.
- Store ledger IDs on heartbeat runs and run events.
- Add APIs for run-level and issue-level context ledger inspection.
- Add UI visibility for prompt class, estimated tokens, actual tokens, cached tokens, budget status, pack refs, and cursor state.

Tests:

- Migration/schema tests.
- Heartbeat service unit tests for bootstrap, resume, timer, comment, and recovery prompts.
- Route tests for ledger readback.
- Cursor race and stale comment tests.
- Budget hard-stop tests before subprocess spawn.
- UI tests for ledger display.

### 3. `hermes-agent`: artifact-backed replay and content-addressed blocks

Implement third because it changes the transcript substrate and has the highest direct token savings.

Required changes:

- Add schema migration for artifacts, message artifact links, replay content, search content, and prompt blocks.
- Update `append_message()` to artifactize large content and tool results.
- Update `get_messages_as_conversation()` to materialize bounded replay, not raw historical payloads, unless exact replay is explicitly requested.
- Preserve FTS by indexing `search_content`.
- Preserve audit by retaining exact artifact blobs.
- Ensure tool-call/tool-result pairing remains valid.
- Include API server and gateway session stores, not only CLI.
- Decide and document how `/v1/responses` storage participates.

Tests:

- Migration from existing DB.
- FTS finds content stored in artifacts.
- Large tool outputs replay as bounded pointers.
- Current-turn and recent decisive tool groups replay exactly.
- Prompt cache markers remain stable for unchanged prefixes.
- CLI, gateway, and API-server resume tests.
- ROI fixture proving rough-token replay reduction.

### 4. `paperclip`: run-log compaction

Implement in parallel after ledger design is stable.

Required changes:

- Stop storing repeated full streaming assistant snapshots as independent large JSONL chunks.
- Store deltas plus final snapshot, or collapse snapshot families at finalize time.
- Compress or chunk large logs with indexed readback.
- Track storage bytes by run, adapter, company, and event type.

Tests:

- Streaming transcript reconstruction remains correct.
- Final assistant state is preserved.
- Log read API still returns expected excerpts.
- Hash/byte accounting remains stable.
- Storage shrink fixture for repeated `message_update` payloads.

### 5. `portfolio-os`: context-pack envelope and routing enforcement

Implement after adapter/Paperclip telemetry can receive pack metadata.

Required changes:

- Emit a context-pack envelope in Hermes task bundles.
- Include manifest path, index path, repo slug, default profile, allowed profiles, selected pack, SHA, bytes, estimated tokens, pack HEAD, current HEAD, dirty count, freshness, and budget.
- Require explicit escalation for delta/core packs.
- Report stale packs as stale, not silently acceptable.
- Prevent symlink/profile spoofing by validating pack paths against the manifest.

Tests:

- Envelope validation.
- Fresh/stale detection.
- Map-first selection.
- Explicit delta/core escalation.
- Dirty-tree reporting.
- Manifest SHA propagation into Paperclip ledger.

### 6. `gstack`, GBrain, Graphify: optional retrieval pilot

Implement only after the ledger and pack envelope exist.

Required changes:

- Index ledger events, task bundles, POS artifacts, context-pack refs, and outcome summaries.
- Produce bounded `retrieval_context.json`, never raw unbounded prompt insertions.
- Attach retrieval result IDs and pack SHAs to ledger entries.
- Use Graphify for relationship queries, not heartbeat prompt compression.
- Use GBrain only when configured and on PATH, with privacy stop-gates intact.

Tests:

- Deterministic retrieval fixture.
- Bound enforcement.
- Provenance attached to every retrieval item.
- No prompt mutation mid-Hermes-session.

## Design Rules

1. Raw transcript is the audit log, not the default replay payload.
2. A resume prompt without a prompt class is a bug.
3. A prompt component without a hash is unaccountable.
4. A context pack without a manifest SHA and freshness status is not production context.
5. A tool result over the replay cap must become an artifact pointer plus summary.
6. Graph retrieval cannot compensate for missing budgets.
7. Exact duplicate prompt hashing is insufficient; component fingerprints are required.
8. Do not break Hermes prompt caching by mutating active historical context.
9. Do not paste core packs by default.
10. Store enough exact evidence that every budget decision is explainable after the fact.

## Immediate Definition of Done

The next implementation tranche should be considered complete only when all of the following are true:

- A Hermes Paperclip resumed run emits `promptClass=resume_delta`.
- The same run has component hashes, char totals, rough token totals, and a budget version.
- Paperclip writes a context ledger entry before adapter execution.
- Budget violations are caught before spawning Hermes.
- Hermes can store a large tool output as an exact artifact while replaying only a deterministic bounded pointer.
- FTS can still find archived artifact-backed content.
- Context pack profile, pack SHA, manifest SHA, HEAD, dirty count, and freshness are visible in telemetry.
- Tests prove replay token reduction on a fixture that previously exceeded 250,000 rough tokens.
- The run-log store no longer grows by repeated full assistant snapshots for the same stream family.

## Residual Risks

- Prompt-cache byte drift: content-addressed blocks must not change active system prompt bytes until byte-identical reconstruction is proven.
- Tool-call protocol validity: bounded replay cannot break assistant/tool message pairing.
- Search regression: artifactizing content must not make old tool evidence undiscoverable.
- Ledger secrecy: raw prompts and tool outputs may contain secrets, so ledger components need redaction classes and access controls.
- Cursor races: comment and wake cursors must be monotonic and scoped by company/agent/task.
- Stale pack trust: map-first behavior is only safe if pack freshness is enforced.
- Runtime mismatch: live DB state should be queried directly for rollout decisions; nearby SQLite files are not authoritative for Paperclip cockpit runtime.

## Final Recommendation

Build the ledger and prompt-class spine first, then replace Hermes raw replay with artifact-backed materialization, then add context-pack enforcement. That sequence delivers direct token savings, keeps auditability, and creates the evidence layer needed for later Graphify/GBrain retrieval.

Do not start with Graphify or vectors. They become valuable after every retrieved item can point back to a ledger entry, pack SHA, run ID, issue ID, and budget class.

