# Hermes Upstream Cutover Runbook

Date: 2026-06-15

Cutover branch: `codex/hermes-upstream-paperclip-cutover`

Upstream base: `upstream/main` at `ae433634db562e644175d39537ef6b811a381f3f`

## What Changes

This cutover moves the Portfolio-OS adapter from a fork-only top-level package into the upstream Hermes plugin surface:

- `plugins/portfolio_os`: bundled standalone plugin for `hermes portfolio-os`.
- `portfolio_os_adapter`: compatibility package that re-exports the plugin modules for old imports.
- `hermes chat --disable-fallback-model`: automation-safe hard-stop flag preserved for Paperclip.
- `HERMES_DISABLE_FALLBACK_MODEL=1`: env equivalent used by the external adapter.
- `hermes_state.py`: legacy `state.db` migration fix so schema-7-style DBs can reconcile missing columns before indexes are created.

The Paperclip external adapter launch contract stays unchanged:

```bash
hermes chat -Q -q "$PROMPT" --source paperclip --disable-fallback-model
```

The adapter should continue setting:

```bash
HERMES_SESSION_SOURCE=paperclip
HERMES_DISABLE_FALLBACK_MODEL=1
```

## Production Preconditions

Do not cut over production until all of these are true:

- Paperclip scheduling/dispatch is paused or the target agent is drained.
- No active Hermes Paperclip runs are still writing to `~/.hermes/state.db`.
- A timestamped backup of `~/.hermes/state.db`, `~/.hermes/config.yaml`, and the Paperclip adapter config exists.
- The upstream install is on this branch or a reviewed commit that includes the same changes.
- `plugins.enabled` includes `portfolio-os` in the Hermes profile that Paperclip will use.
- The Paperclip adapter still has `disableFallbackModel` enabled or sets `HERMES_DISABLE_FALLBACK_MODEL=1`.
- MiniMax-only or explicitly approved provider routing is configured before re-enabling Paperclip dispatch.

Enable the plugin:

```yaml
plugins:
  enabled:
    - portfolio-os
```

## Preflight

Run from the candidate upstream checkout:

```bash
scripts/run_tests.sh \
  tests/plugins/test_portfolio_os_plugin.py \
  tests/hermes_cli/test_disable_fallback_model_flag.py \
  tests/cli/test_cli_init.py
```

Expected result:

```text
55 tests passed
```

Then verify the command is visible only when enabled:

```bash
HERMES_HOME=/path/to/test-hermes-home python -m hermes_cli.main portfolio-os --help
HERMES_HOME=/path/to/test-hermes-home python -m hermes_cli.main --safe-mode portfolio-os --help
```

The first command should show Portfolio-OS subcommands. The safe-mode command should reject `portfolio-os`.

## Canary Sequence

1. Create a dry-run bundle against a disposable local git repo.
2. Validate it:

```bash
hermes portfolio-os validate-bundle --bundle /path/to/bundle.json
```

3. Dry-run it:

```bash
hermes portfolio-os dry-run --bundle /path/to/bundle.json
```

4. Dispatch it against the disposable repo:

```bash
hermes portfolio-os dispatch --bundle /path/to/bundle.json
```

5. Confirm the result artifact:

```bash
hermes portfolio-os status --run-id <run-id> --portfolio-os-root /path/to/portfolio-os
```

6. Run one Paperclip adapter canary with `--disable-fallback-model` and confirm:

- stdout contains only the final Hermes response.
- stderr contains the session id.
- `sessions.source` is `paperclip`.
- usage columns read correctly: input/output/cache/reasoning tokens, cost fields, billing provider/base URL/mode, model.
- no fallback provider is activated after primary provider auth or runtime failure.

## Rollback

Rollback is a configuration switch, not a data rewrite:

1. Pause Paperclip dispatch again.
2. Point Paperclip back to the prior Hermes command/path.
3. Remove `portfolio-os` from `plugins.enabled` if needed.
4. Restore `~/.hermes/state.db` from the timestamped backup only if migration or usage reads regress.
5. Re-run the Paperclip adapter canary on the prior Hermes path before unpausing.

## Caveats

- The Portfolio-OS command is an opt-in standalone plugin. A production Hermes profile without `plugins.enabled: [portfolio-os]` will not expose `hermes portfolio-os`.
- `--safe-mode` intentionally disables the plugin command.
- The historical `bin/hermes` wrapper is not part of upstream. Production should use the installed `hermes` console script or `python -m hermes_cli.main`.
- `--disable-fallback-model` disables configured fallback providers. That preserves Paperclip hard-stop policy but also means provider outage becomes a blocked run unless Paperclip explicitly approves a routing change.
- The state DB migration fix covers missing `sessions.parent_session_id` before index creation; it does not change FTS repair behavior. Keep the state DB backup.
- This runbook does not authorize switching from MiniMax to paid OpenAI, Claude, Gemini, or other subscription lanes without an explicit approval gate.

## Execution Evidence

Operational receipts are stored under:

```text
/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/runs/
```

Key receipts:

- Phase 0 preflight: `20260615T185816Z-phase0-preflight.json`.
- Phase 2 freeze: `20260615T192900Z-phase2-freeze-starts.json`.
- Phase 3 snapshot: `20260615T193200Z-phase3-snapshot.json`.
- Phase 6 successful live HTTP canary: `20260615T200400Z-phase6-live-http-canary.json`.
- Phase 7 fleet config widening: `20260615T200958Z-phase7-hermes-config-widening.json`.
- Phase 8 schedule restore: `20260615T201331Z-phase8-unfreeze-routine-triggers.json`.
- Phase 8 timer restore: `20260615T201649Z-phase8-unfreeze-timers.json`.
- Phase 9 final validation: `20260615T202503Z-phase9-final-validation.json`.
- Phase 10 final screen server validation: `20260615T203831Z-phase10-final-screen-server-validation.json`.

Verified production facts from this cutover:

- Paperclip stayed authenticated/private/healthy during the cutover.
- Execution was frozen before snapshot and config writes: `0` active heartbeat runs, `0` pending wake requests, `0` enabled routine triggers, `0` enabled Hermes timer heartbeats.
- State rollback anchors were captured for `~/.hermes/state.db`, `~/.hermes/config.yaml`, and Paperclip Postgres.
- `~/.hermes/config.yaml` now enables the `portfolio-os` Hermes plugin.
- All `56` `hermes_local` Paperclip agents are pinned to `/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes`.
- All `56` `hermes_local` agents are pinned to `source=paperclip` and `disableFallbackModel=true`.
- All `52` tiered `hermes_minimax` lanes are pinned to the same command/source/hard-stop flags while preserving provider/model and approval policy.
- Live canary run `4ee10d9f-4470-4a59-80e0-327c180e6940` succeeded with process metadata, `source=paperclip`, MiniMax billing provider, MiniMax Anthropic base URL, and Hermes state DB usage.
- Schedule restore used an explicit audible: `53` saved triggers were overdue, so unfreeze recalculated each schedule's next future cron tick instead of replaying stale historical due times.
- After unfreeze and final runtime validation, Paperclip had `68` enabled routine triggers, `2` enabled Hermes timer heartbeats, `0` running heartbeat runs, `0` queued heartbeat runs, `0` pending or claimed wake requests, and `0` due active schedules.
- Paperclip is running in detached screen session `paperclip-cockpit-cutover`, with Node PID `24406` listening on TCP `*:3100`.
- The failed LaunchAgent attempt was removed after macOS TCC blocked it; `launchctl` no longer has the service loaded and the generated plist/helper no longer exist.

Verification commands:

- Hermes cutover targeted suite:
  `scripts/run_tests.sh tests/run_agent/test_session_source.py tests/hermes_cli/test_disable_fallback_model_flag.py tests/cli/test_cli_init.py`
  - Result: `46 tests passed`.
- External enhanced Paperclip adapter:
  `npm test` in `/Users/mnm/Documents/Github/hermes-paperclip-adapter`
  - Result: `29 tests passed`.
- Paperclip in-tree compatibility/routing checks:
  `pnpm test:run server/src/__tests__/hermes-local-compat-adapter.test.ts server/src/__tests__/opencode-go-role-routing.test.ts`
  - Result: `50 tests passed`.
- Paperclip server typecheck:
  `pnpm --filter @paperclipai/server typecheck`
  - Result: passed.
- Hermes full suite:
  `source .venv/bin/activate && scripts/run_tests.sh tests/`
  - Result: `1486 files, 31624 tests passed, 0 failed` in `298.9s`.

## Adapter Caveats

- Do not cut production to the official npm `hermes-paperclip-adapter@0.2.0` package yet.
- The currently enhanced external adapter at `/Users/mnm/Documents/Github/hermes-paperclip-adapter/index.js` remains the production adapter because it preserves Paperclip-specific requirements: `HERMES_SESSION_SOURCE=paperclip`, `--disable-fallback-model`, MiniMax/OpenCode routing policy, Hermes state DB usage reads, managed Paperclip skill preload, and Paperclip ownership language.
- The official package lacks the complete Paperclip launch contract and includes behavior that would be unsafe for this fleet, including insufficient source/hard-stop handling and prompt language that can encourage self-assignment of unassigned work.
- Paperclip now also has an in-tree `hermes_local` compatibility adapter as a fallback safety net, but the live server still prefers the external enhanced adapter override.

## Remaining Watch Items

- The Paperclip server is operational in detached `screen`, not a durable macOS LaunchAgent. The LaunchAgent attempt was intentionally removed after local TCC blocked access to the instance `.env` under `Documents`.
- Pre-existing agent statuses were not mass-cleared: `24` Hermes agents remained in `error` before and after cutover. That is a fleet-work backlog, not a cutover blocker, because active/pending work is zero and canary execution is green.
- `19` enabled routine triggers currently have past `next_run_at` values, but all belong to archived or paused routines. Current due active schedule count is `0`.
- `--disable-fallback-model` intentionally converts provider outage into a blocked run unless Paperclip explicitly approves a routing change after MiniMax exhaustion.
- Paid OpenAI, Claude, Gemini, or other subscription lanes remain unauthorized without explicit approval.
