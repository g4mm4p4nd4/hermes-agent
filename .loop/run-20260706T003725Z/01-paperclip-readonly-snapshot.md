# Paperclip Read-Only Runtime Snapshot

Phase: 1
Status: complete
Mode: read-only DB/API queries only, per Q3.

## Health

API:

```bash
curl -sS http://127.0.0.1:3100/api/health | jq .
```

Observed:

- status: `ok`
- version: `0.3.1`
- deployment mode: `authenticated`
- exposure: `private`
- auth ready: `true`
- bootstrap status: `ready`
- company deletion enabled: `false`

Runtime processes:

- Postgres listening on `127.0.0.1:54329` and `[::1]:54329`.
- Node listening on `*:3100`.
- `psql` is not on PATH, so DB probes used package-scoped Node with the `postgres` client inside read-only transactions.

## Companies

| Company | Prefix | Status | Issue Counter |
| --- | --- | --- | --- |
| LeadForge company | `POR` | active | 2740 |
| Portfolio OS Orchestrator | `PORA` | active | 1972 |
| YT-Synth | `PORAA` | active | 3228 |
| agency-swarm | `PORAAA` | active | 133 |

## Agent State Problems

- Portfolio OS Orchestrator: Portfolio Cartographer and Venture Factory Liaison are terminated with old heartbeats.
- LeadForge: QA is in `error`, last heartbeat `2026-07-04T19:27:17.346Z`.
- YT-Synth: CMO run completed after the snapshot; Designer and Copy are terminated.
- agency-swarm: CMO, Designer, Copy, Engineer-1, Engineer-2, Growth/Distribution, QA, and Release Manager are paused; CEO is running; Skill Curator is terminated.

## Routine State

Last 24h routine outcomes:

- Portfolio OS Orchestrator: coalesced 3, completed 1, issue_created 1, skipped 43.
- LeadForge: skipped 10.
- YT-Synth: skipped 6.
- agency-swarm: coalesced 2, skipped 3.

Last 72h meaningful failures:

- `Signal Desk :: Evidence Intake Gate`, manual, failed `2026-07-04T20:30:12.422Z`, reason `Execution issue moved to blocked`, linked `PORA-1936`.
- `Signal Desk :: Evidence Intake Gate`, manual, failed `2026-07-04T20:16:21.812Z`, linked `PORA-1930`.

Open routine issues:

- `PORA-1957 Council Chamber :: Existing Venture Gate`, `in_progress`, updated `2026-07-05T13:32:57.099Z`.
- `PORA-1936 Signal Desk :: Evidence Intake Gate`, `in_progress`, updated `2026-07-06T00:37:40.657Z`.

## Live Log Failure Found During Restart Prep

Paperclip log path: `/tmp/paperclip-screen-fallback.log`

Observed failure:

```text
GET /api/issues/34d9b7f4-3b65-4d88-b8e5-a66e7146834c/comments?after=6ac3764a-2480-406c-a0fb-ffe1dcb6cbf4&order=asc 500
TypeError [ERR_INVALID_ARG_TYPE]: The "string" argument must be of type string or an instance of Buffer or ArrayBuffer. Received an instance of Date
```

Cause:

- `issueService.listComments()` selected the anchor comment timestamp as a JavaScript `Date`.
- The code embedded that `Date` directly into a raw SQL cursor comparison.
- The `postgres` driver rejected the Date binding in that raw SQL fragment.

Fix applied:

- Commit `61b9fdae9 fix(issues): normalize comment cursor timestamps`.
- Normalize the anchor timestamp to an ISO string and cast it as `timestamptz` in the cursor SQL.
- Add an embedded Postgres regression test for both ascending and descending comment cursor pagination.

## Post-Fix Restart Receipt

Restart action:

- The original fallback `screen` restart left an orphaned old server on port 3100 and a new server on port 3101.
- Both Paperclip server process groups were terminated.
- A single fallback `screen` session was started again with `pnpm --filter @paperclipai/server dev`.

Health after cleanup:

```json
{"status":"ok","version":"0.3.1","deploymentMode":"authenticated","deploymentExposure":"private","authReady":true,"bootstrapStatus":"ready","bootstrapInviteActive":false,"features":{"companyDeletionEnabled":false}}
```

Listener state:

- `node` PID `17959` is listening on `*:3100`.
- No listener remained on `3101`.
- Startup log reports `Server listening on 0.0.0.0:3100`.

Loaded canary target reality after restart:

```json
[
  {"repoSlug":"leadforge","cwd":"/Users/mnm/Documents/Github/LeadForge"},
  {"repoSlug":"paperclip","cwd":"/Users/mnm/Documents/Github/paperclip"},
  {"repoSlug":"hermes-agent","cwd":"/Users/mnm/Documents/Github/hermes-agent"},
  {"repoSlug":"portfolio-os","cwd":"/Users/mnm/Documents/Github/portfolio-os"},
  {"repoSlug":"yt-synth","cwd":"/Users/mnm/Documents/Github/YT-Synth"},
  {"repoSlug":"agency-swarm","cwd":"/Users/mnm/Documents/Github/agency-swarm"},
  {"repoSlug":"gstack","cwd":"/Users/mnm/Documents/Github/gstack"}
]
```

## Live Run Evidence

Run: `99bb0ff0-c1a7-4fba-9163-bb5d078f3471`

- Company: YT-Synth
- Agent: CMO
- Issue: `PORAA-3207 Reissue GTM as community-channel pack, gated to v0.4.0 tag`
- Adapter: `hermes_local`
- Runtime: Hermes v0.16.0 from `/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes`
- Provider lane: `opencode-go` / `kimi-k2.6`
- Prompt class: `context_manifest`
- Result: succeeded technically, but returned blocked work rather than a cake artifact.

Usage:

- input tokens: 81,329
- output tokens: 10,855
- cached input tokens: 1,011,712
- session reused: true
- task session reused: true
- selected skills: `paperclip/paperclip`, `paperclip/paperclip-go-to-market`, `paperclip/paperclip-product-scope`, `paperclip/para-memory-files`, `paperclip/ponytail`

Blocked result:

- DOD 1-3 and DOD 6 were satisfied.
- DOD 4-5 were blocked by missing HN, Reddit, Product Hunt, dev.to, X, and Discord credentials plus incomplete warm-up.
- `PORAA-3220` has 7 drafts and 0 actual posts.

## Cake Metric

This run consumed a large token envelope to conclude "blocked" with no deployable, revenue-moving artifact. That is not acceptable cake output. It is a high-value failure signal for blocker fingerprinting and no-op rerun suppression.
