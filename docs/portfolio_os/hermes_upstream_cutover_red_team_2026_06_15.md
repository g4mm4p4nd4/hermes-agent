# Hermes Upstream Cutover Red-Team Review - 2026-06-15

## Scope

This is an adversarial review of the existing Hermes upstream cutover documents.
It asks what a production cutover could still miss even if the current
assessment, graph map, inventory, and matrix are followed.

The review focuses on failure modes that would break Paperclip production,
silently lose Hermes/Paperclip features, create unauthorized provider spend, or
make rollback unreliable.

## Verdict

The cutover package is a strong planning base, but it is not production-safe
until the blockers below are converted into explicit gates. The highest-risk
gap is not abstract: the external Paperclip adapter currently invokes
`hermes chat -Q -q <prompt> --source paperclip --disable-fallback-model`, and
`upstream/main` has no observed `--disable-fallback-model` or
`HERMES_DISABLE_FALLBACK_MODEL` support. Pointing Paperclip at upstream Hermes
without adding an equivalent guard would either fail argument parsing or remove
the hard stop that prevents disallowed fallback escalation.

Directly merging upstream is also not viable. A non-destructive merge forecast
returned conflicts in CLI, provider fallback, gateway, session state, tests, and
operator docs. The safe path remains a new branch from `upstream/main` plus an
intentional Paperclip/Hermes integration port.

## P0 Production Blockers

| ID | Missing or weak area | Evidence | Production failure mode | Required gate |
| --- | --- | --- | --- | --- |
| RT-P0-01 | Upstream CLI does not expose the current fallback-disable contract | `git grep -n "disable-fallback-model\|HERMES_DISABLE_FALLBACK_MODEL" upstream/main -- .` returned no matches; current `venv/bin/hermes chat --help` exposes `--disable-fallback-model`; external adapter emits that flag and `HERMES_DISABLE_FALLBACK_MODEL=1` | Paperclip `hermes_local` runs fail at CLI parse time, or a replacement command accidentally permits fallback beyond MiniMax | Implement upstream-compatible hard-stop semantics, update external adapter if the flag is renamed, and run `createServerAdapter().testEnvironment()` against the new Hermes binary |
| RT-P0-02 | Direct merge conflict budget is not explicit enough | `git merge-tree --write-tree --name-only HEAD upstream/main` exits `1` with conflicts in `cli.py`, `run_agent.py`, `gateway/run.py`, `hermes_state.py`, `hermes_cli/config.py`, `hermes_cli/main.py`, `pyproject.toml`, ACP files, provider docs, and many tests | Conflict resolution can silently drop local provider, state, CLI, or Paperclip behavior | Ban direct merge in the runbook; require an upstream-based cutover branch and a file-by-file conflict retirement ledger |
| RT-P0-03 | Live Paperclip inventory is not a hard preflight | Existing docs mention canary and guard, but do not require a live inventory of active `hermes_local` agents, adapter configs, heartbeats, pending runs, wakeups, approval flags, and runtime routing state | Static repo correctness can pass while live Paperclip keeps dispatching through old or unsafe adapter settings | Before any switch, snapshot the live Paperclip DB/config and produce counts for active runs, queued runs, `hermes_local` agents, heartbeat-enabled agents, routines, scheduled wakes, and provider approvals |
| RT-P0-04 | Paid-provider hard gate is described but not mechanically proven | Paperclip policy requires MiniMax-first recovery and no OpenAI, Claude, Gemini, or other paid fallback without explicit approval; upstream has generic `fallback_providers` | A global upstream fallback chain can spend on a denied provider during failure recovery | Add tests that monkeypatch provider clients and assert MiniMax exhaustion writes a blocked result and invokes no denied provider without an approval receipt |
| RT-P0-05 | Hermes state database migration and adapter usage accounting are not proven | Local `hermes_state.py` is `SCHEMA_VERSION = 7`; upstream is `SCHEMA_VERSION = 16`; external adapter reads `state.db` session usage and cost fields | Cutover can break usage/cost accounting, session resume, source filtering, or state migration even if chat responses work | Snapshot production `~/.hermes/state.db`, migrate a copy with upstream code, run adapter usage extraction against that migrated copy, and verify `source=paperclip` sessions still behave |

## P1 Cutover Gaps

| ID | Missing or weak area | Why it matters | Required gate |
| --- | --- | --- | --- |
| RT-P1-01 | External adapter tests are current-Hermes only | `npm test` proves the current adapter in isolation, not compatibility with upstream Hermes | Run adapter tests with `hermesCommand` pointed at the upstream cutover binary, then run `testEnvironment()` with real Paperclip routing config |
| RT-P1-02 | Plugin enablement path is underspecified | Upstream plugin loading is opt-in unless bundled; `safe-mode` or config isolation can hide `hermes portfolio-os` | Prove `hermes plugins list` and `hermes portfolio-os --help` work in the exact environment and `HERMES_HOME` Paperclip will use |
| RT-P1-03 | Scheduler pause/resume mechanism is vague | Historical Paperclip drain-freeze receipts show `heartbeatEnabled`, `pauseReason`, and `pausedAt`; the cutover docs do not name the exact pause/resume command, API, SQL, or receipt authority | Add a drain/freeze step with pre/post counts, receipt path, restore path, and a hard stop if any `hermes_local` run remains active |
| RT-P1-04 | Credential and environment isolation are not explicit | Upstream can read richer config and fallback chains than the old fork; Paperclip production must not inherit operator-only paid keys by accident | Document exact `HERMES_HOME`, env file, provider keys, fallback config, and denied-key checks for the production Hermes profile |
| RT-P1-05 | Python Portfolio-OS adapter inference preflight is still conceptual | External adapter has provider/model checks; the Python adapter can still mutate target repos before discovering inference is down unless a pre-dispatch probe is added | Add a pre-mutation provider resolution/probe and tests for missing credentials, stale `api_mode`, MiniMax exhaustion, and blocked artifact output |
| RT-P1-06 | Output contract decision is not tied to Paperclip artifacts | Upstream token handling is better, but local compact output behavior is not upstream | Decide global versus adapter-local output bounding, then test status/result/log artifact sizes and fields |
| RT-P1-07 | Fresh upstream environment validation is missing | The current local `venv` has no `pip`; upstream uses `uv.lock`, stricter pins, and package data | Build a fresh cutover env, then run `hermes --version`, import smoke, `hermes chat -Q -q`, `hermes plugins list`, and package-data checks |
| RT-P1-08 | Rollback is reversible in principle, not yet rehearsed | If the old `venv/bin/hermes` path is replaced in place, rollback can fail under pressure | Use a new binary/symlink path, switch Paperclip atomically, then rehearse rollback and re-run current adapter `testEnvironment()` |
| RT-P1-09 | Canary authority is underspecified | Existing docs say run guard/canary, but not which receipt wins when dashboards or latest pointers disagree | Name immutable receipt paths as authority, require current timestamped guard/canary receipts, and treat missing receipt fields as blockers |

## P2 Completeness Gaps

| ID | Gap | Required hardening |
| --- | --- | --- |
| RT-P2-01 | Graphify-native graph artifact is still missing | Either install/repair the Graphify extraction capability or explicitly accept the manual graph artifact as the signoff source |
| RT-P2-02 | Security/secret scan is absent from the cutover gates | Run a secrets scan over the cutover branch and generated docs before publishing or switching production |
| RT-P2-03 | Prompt-cache/cost regression is not measured | Add a before/after sample run that records context size, cache use, output size, and provider biller metadata |
| RT-P2-04 | Skills and command docs can drift | Regenerate CLI help/reference docs from the cutover binary and verify Paperclip docs match the enabled command surface |

## Attack Scenarios

1. Paperclip switches `hermesCommand` to the upstream binary. The first
   scheduled `hermes_local` run still includes `--disable-fallback-model`.
   Upstream rejects the unknown argument, the run fails before producing the
   expected blocked Paperclip artifact, and scheduled wakes continue retrying.

2. A maintainer removes `--disable-fallback-model` from the external adapter to
   make upstream parsing pass. The upstream `fallback_providers` chain still
   contains Claude, OpenAI, Gemini, or another paid lane. A MiniMax outage turns
   into unauthorized fallback spend instead of a blocked result.

3. The cutover branch migrates `~/.hermes/state.db` in place. Chat works, but
   the external adapter no longer reads the expected usage/cost/session fields
   or source filtering changes behavior. Paperclip cost accounting and session
   continuity become wrong without an obvious runtime error.

4. The Portfolio-OS command is ported as a plugin but not enabled in the
   production profile. Manual `hermes chat` smoke tests pass, while Paperclip
   bundle dispatch fails because `hermes portfolio-os` is absent in the real
   environment.

5. The old Hermes path is overwritten in place. The canary fails on Paperclip
   artifact schema or provider policy, but rollback requires rebuilding the old
   environment instead of flipping a known-good path back.

6. Cutover tests run against static fixtures only. Live Paperclip still has
   heartbeat-enabled `hermes_local` agents, scheduled wakes, or queued runs that
   dispatch during the switch and produce mixed old/new receipts.

## Required Additions To The Cutover Package

1. Add a preflight script or documented command set that snapshots live
   Paperclip state and reports:
   `hermes_local` adapter registrations, active and queued runs, heartbeat
   counts, paused agents, scheduled wakes, fallback approval flags, selected
   Hermes command paths, and provider routing configs.

2. Add an explicit external adapter compatibility gate:
   `npm test`, `testEnvironment()` against the cutover Hermes binary, a real
   `hermes chat -Q -q smoke --source paperclip` invocation, and a session usage
   read from the selected `HERMES_HOME/state.db`.

3. Add a state migration gate:
   copy production `state.db`, run upstream migration on the copy, create or
   resume a `source=paperclip` session, and verify token/cost/session fields
   through the external adapter reader.

4. Add a provider-denial gate:
   run simulated primary failure, MiniMax failure, and denied fallback scenarios
   while asserting no OpenAI, Claude, Gemini, or other denied provider client is
   invoked without an explicit approval artifact.

5. Add a drain/freeze and restore runbook:
   exact command/API/SQL, immutable receipt path, pre/post counts, restore
   command, and a stop condition if anything remains active.

6. Add a rollback rehearsal:
   switch Paperclip to the new Hermes path, run a small canary, switch back to
   the old path, and prove the current external adapter still passes
   `testEnvironment()`.

7. Add conflict-retirement tracking:
   each conflicted file from the merge forecast must map to one of
   `use_upstream`, `port_local_behavior`, `replace_with_plugin`, or `drop_with_test`.

## Release Gate

Do not proceed to production cutover until every P0 is closed with current
evidence and every P1 has either a passing gate or an explicit signed exception.
The current docs are sufficient for planning the cutover branch. They are not
sufficient as the production switch runbook until the missing live-state,
provider-denial, state-migration, plugin-enable, and rollback gates are added.

## Evidence Commands

```bash
git grep -n "disable-fallback-model\|HERMES_DISABLE_FALLBACK_MODEL" upstream/main -- . || true
source venv/bin/activate && venv/bin/hermes chat --help | rg -n "disable-fallback-model|provider|source|query|quiet"
git merge-tree --write-tree --name-only HEAD upstream/main
git show HEAD:hermes_state.py | rg -n "SCHEMA_VERSION|input_tokens|output_tokens|billing_provider"
git show upstream/main:hermes_state.py | rg -n "SCHEMA_VERSION|input_tokens|output_tokens|billing_provider|archived|rewind_count"
rg -n "disable-fallback-model|HERMES_DISABLE_FALLBACK_MODEL|state.db|testEnvironment|buildHermesArgs" /Users/mnm/Documents/Github/hermes-paperclip-adapter
rg -n "MiniMax|post-MiniMax|fallback|OpenAI|Claude|Gemini|heartbeatEnabled|pauseReason" /Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/docs /Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/logs/drain-freeze
```
