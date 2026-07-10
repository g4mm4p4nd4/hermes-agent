# Hermes/Paperclip Operational Recovery Plan

Date: 2026-06-15

Working branch: `codex/hermes-upstream-paperclip-cutover`

Working tree: `/Users/mnm/Documents/Github/hermes-agent-upstream-cutover`

Primary runbook: `docs/portfolio_os/hermes_upstream_cutover_runbook_2026_06_15.md`

## Execution Status

Status as of 2026-06-15T20:38Z: cutover executed and systems operational.

Production receipts are under:

```text
/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/runs/
```

Completed phases:

- Phase 0 preflight: Paperclip healthy/private/authenticated; no active runs or pending wakes.
- Phase 1 release gate: targeted Hermes tests, external adapter tests, Paperclip compatibility tests, Paperclip server typecheck, and the Hermes full suite are green. Full Hermes result: `1486 files, 31624 tests passed, 0 failed` in `298.9s`.
- Phase 2 freeze: `68` routine triggers and `2` Hermes timer heartbeats disabled; active/pending execution drained to `0`.
- Phase 3 snapshot: Hermes state/config and Paperclip Postgres backups captured with checksums.
- Phase 4 cutover config: `portfolio-os` plugin enabled and cutover Hermes command verified.
- Phase 5 provider/source canary: MiniMax raw canary green; `source=paperclip` bug fixed and covered by test.
- Phase 6 live canary: Paperclip HTTP wake succeeded with process metadata, `source=paperclip`, MiniMax billing metadata, and Hermes state usage.
- Phase 7 fleet widening: all `56` `hermes_local` agents pinned to cutover command, `source=paperclip`, and fallback-disabled; all `52` tiered MiniMax lanes pinned the same way.
- Phase 8 unfreeze: `68` routine triggers and `2` Hermes timers restored; an audible recalculated stale schedule `next_run_at` values to future cron ticks to avoid replaying weeks of backlog.
- Phase 9 final validation: `20260615T202503Z-phase9-final-validation.json` passed with no failures.
- Phase 10 runtime validation: `20260615T203831Z-phase10-final-screen-server-validation.json` passed with no failures. Paperclip is running in detached screen session `paperclip-cockpit-cutover`, serving `http://127.0.0.1:3100`, with the failed LaunchAgent attempt removed.

Current operational state:

- Paperclip health: `ok`.
- Paperclip server listener: Node PID `24406` on TCP `*:3100`.
- Enabled routine triggers: `68`.
- Enabled Hermes timer heartbeats: `2`.
- Running or queued heartbeat runs: `0`.
- Pending or claimed wake requests: `0`.
- Due active schedules: `0`.
- Due inactive schedules: `19` across archived/paused routines.
- Latest successful canary run: `4ee10d9f-4470-4a59-80e0-327c180e6940`.

Important caveat: keep using the enhanced external adapter at
`/Users/mnm/Documents/Github/hermes-paperclip-adapter/index.js`. The official
npm adapter is not yet production-equivalent for this fleet.

Runtime caveat: the Paperclip server is operational in a detached `screen`
session, not a durable macOS LaunchAgent. The attempted LaunchAgent path was
removed after local TCC restrictions blocked access to the instance `.env` under
`Documents`.

## Goal

Restore Paperclip/Hermes operations on the upstream Hermes cutover while preserving:

- Paperclip session/state/accounting continuity.
- MiniMax-first recovery and hard stop after MiniMax exhaustion.
- No automatic spend into OpenAI, Claude, Gemini, or other paid fallback lanes without explicit approval.
- A reversible production cutover path.
- Clear stop conditions and audibles when live evidence diverges from the expected path.

## Pre-Cutover Verified Snapshot

Captured from local state on 2026-06-15:

- Paperclip server health: `ok`.
- Paperclip deployment mode: authenticated/private.
- Embedded Paperclip Postgres: running on `127.0.0.1:54329`.
- Active heartbeat runs: none.
- Pending wake requests: none.
- Enabled routine triggers: `68`.
- Active routines: `25`.
- `hermes_local` agents: `56`.
- `hermes_local` agents in `error`: `24`.
- Stale `in_progress` issues older than 12 hours: `21`.
- All `hermes_local` agents inherit adapter default command.
- Current adapter default command: `/Users/mnm/Documents/Github/hermes-agent/venv/bin/hermes`.
- Old default Hermes version: `v0.4.0`, 8 commits behind.
- Cutover Hermes command verified executable: `/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes`.
- Cutover Hermes version observed by adapter check: `v0.16.0`.
- `~/.hermes/config.yaml` has no `plugins.enabled` block.
- `~/.hermes/state.db` size: about `2.9G`.
- External `hermes-paperclip-adapter` environment check passes for both old and cutover Hermes commands, with warnings only.

## Non-Negotiable Stop Conditions

Stop immediately and report instead of continuing if any of these are true:

- A live heartbeat run or pending wake appears during a freeze/snapshot/change window.
- Fresh MiniMax canary fails after retryable network checks.
- The adapter does not pass `--disable-fallback-model` or `HERMES_DISABLE_FALLBACK_MODEL=1`.
- A Paperclip canary run writes usage with missing session id, missing `source=paperclip`, or unreadable Hermes state DB accounting fields.
- The cutover Hermes command cannot run `hermes chat --help` and show `--disable-fallback-model`.
- The `portfolio-os` plugin command is unavailable after enabling the plugin.
- Any live command would route into paid fallback lanes without explicit approval.
- A shared project-primary workspace has possible partial mutation and no reviewed workspace receipt.

## Phase 0 - Authority And Baseline

Purpose: lock the exact sources of truth before mutating anything.

Actions:

1. Read this file and the primary cutover runbook.
2. Confirm working tree and branch:

```bash
cd /Users/mnm/Documents/Github/hermes-agent-upstream-cutover
git branch --show-current
git status --short
```

3. Confirm Paperclip health:

```bash
curl -fsS http://127.0.0.1:3100/api/health | jq .
```

4. Confirm no active runs or pending wakes with a read-only DB query.
5. Capture a timestamped preflight receipt under:

```text
/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/runs/
```

Exit criteria:

- Preflight receipt records Paperclip health, active run count, pending wake count, current Hermes command path, routine trigger count, and current `~/.hermes/config.yaml` plugin state.

Audibles:

- If Paperclip health is down, fix/restart Paperclip before touching Hermes.
- If active runs or pending wakes exist, pause and drain before continuing.
- If the branch has unrelated dirty changes, do not stage/revert them; record and continue only if they do not affect the cutover.

## Phase 1 - Finish Hermes Release Gate

Purpose: make the cutover branch acceptable as the candidate execution binary.

Actions:

1. Ensure the cutover venv is real and local, not a symlink to the old checkout:

```bash
cd /Users/mnm/Documents/Github/hermes-agent-upstream-cutover
readlink .venv || true
.venv/bin/python - <<'PY'
import agent.model_metadata, hermes_cli.auth, plugins.portfolio_os
print(agent.model_metadata.__file__)
print(hermes_cli.auth.__file__)
print(plugins.portfolio_os.__file__)
PY
```

2. Install missing optional test dependencies needed by the upstream suite:

```bash
uv sync --extra dev --extra acp
.venv/bin/python -m pip install defusedxml
```

3. Run the cutover suite:

```bash
scripts/run_tests.sh \
  tests/plugins/test_portfolio_os_plugin.py \
  tests/hermes_cli/test_disable_fallback_model_flag.py \
  tests/cli/test_cli_init.py \
  tests/hermes_state \
  tests/test_state_db_malformed_repair.py \
  tests/test_empty_session_hygiene.py \
  tests/hermes_cli/test_plugin_cli_registration.py \
  tests/hermes_cli/test_ignore_user_config_flags.py
```

4. Run the external adapter tests:

```bash
cd /Users/mnm/Documents/Github/hermes-paperclip-adapter
npm test
```

5. Run or resume the full Hermes test suite:

```bash
cd /Users/mnm/Documents/Github/hermes-agent-upstream-cutover
scripts/run_tests.sh
```

6. Fix remaining genuine full-suite failures. Known failure to resolve:

- `tests/gateway/test_gateway_shutdown.py::test_gateway_stop_systemd_service_restart_exits_cleanly`
  expected `_exit_code == 0` under systemd shortcut restart, while current behavior returns the service restart exit code.

Exit criteria:

- Cutover suite green.
- External adapter suite green.
- Full suite green, or explicit operator approval to proceed with a documented full-suite exception.
- `git diff --check` clean.

Audibles:

- If full suite is blocked only by environment-only optional dependencies, install the missing dependency and rerun.
- If full suite exposes unrelated upstream failures, fix them when small and safe.
- If unrelated failures are large, document exact failures and ask for explicit risk acceptance before touching production execution.

## Phase 2 - Freeze Paperclip Execution

Purpose: prevent live runs from writing state while Hermes command/config changes happen.

Actions:

1. Pause scheduled execution by disabling routine triggers or stopping heartbeat dispatch.
2. Verify:

- Active heartbeat runs: `0`.
- Pending wake requests: `0`.
- No Hermes process spawned by Paperclip is running.

3. Record a freeze receipt with:

- Routine trigger counts before/after.
- Active run count.
- Pending wake count.
- Timestamp.
- Method used to freeze.

Exit criteria:

- No Paperclip execution can start during snapshot and cutover.

Audibles:

- If a run starts during freeze, let it finish or terminate only through the control-plane-safe path, then restart the freeze receipt.
- If routines cannot be disabled cleanly, stop the Paperclip server and embedded scheduler as the fallback freeze method, then snapshot while stopped.

## Phase 3 - Snapshot And Rollback Anchor

Purpose: make rollback data-backed instead of aspirational.

Actions:

1. Snapshot Hermes state/config:

```bash
mkdir -p /Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/backups
ts=$(date -u +%Y%m%dT%H%M%SZ)
cp -p ~/.hermes/state.db "/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/backups/state-${ts}.db"
cp -p ~/.hermes/config.yaml "/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/backups/config-${ts}.yaml"
cp -p /Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/adapter-plugins.json "/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/backups/adapter-plugins-${ts}.json"
cp -p /Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/adapter-settings.json "/Users/mnm/Documents/Github/.paperclip/portfolio-os-cockpit/instances/default/data/ops/hermes-cutover-recovery/backups/adapter-settings-${ts}.json"
```

2. Snapshot Paperclip Postgres using the embedded Postgres tooling or a verified DB export script.
3. Record backup paths and checksums in the cutover receipt.

Exit criteria:

- Hermes state/config backups exist.
- Paperclip DB backup exists.
- Checksums recorded.

Audibles:

- If `~/.hermes/state.db` copy is too slow or space constrained, stop Paperclip and use a compressed copy. Do not proceed without a state DB backup.
- If DB backup tooling is unavailable, stop and install/locate the embedded `pg_dump` equivalent before continuing.

## Phase 4 - Enable Cutover Config

Purpose: make the upstream plugin and hard-stop behavior active before canaries.

Actions:

1. Add the plugin block to `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - portfolio-os
```

2. Verify:

```bash
/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes portfolio-os --help
/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes chat --help | rg -- '--disable-fallback-model|--source|-Q'
```

3. Run adapter environment check against the cutover command:

```bash
node --input-type=module - <<'NODE'
import { testEnvironment } from '/Users/mnm/Documents/Github/hermes-paperclip-adapter/index.js';
const command = '/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes';
const result = await testEnvironment({
  config: { command },
  agent: { id: 'cutover-check', name: 'Cutover Check', adapterType: 'hermes_local', adapterConfig: { command } }
});
console.log(JSON.stringify(result, null, 2));
NODE
```

Exit criteria:

- `portfolio-os` command is visible outside safe mode.
- `--disable-fallback-model` is visible on `chat`.
- Adapter test reports the cutover command executable.

Audibles:

- If plugin command is unavailable, do not edit Paperclip agent config. Fix Hermes plugin loading first.
- If adapter check fails only on optional doctor warnings, continue only if `command_executable`, `version`, and provider model discovery pass.

## Phase 5 - Fresh Provider Canaries

Purpose: avoid restarting systems into known provider failure.

Actions:

1. Run a fresh MiniMax raw canary.
2. Run a Paperclip adapter provider discovery check.
3. Confirm hard-stop policy:

- MiniMax is the first automatic recovery lane.
- Post-MiniMax paid lanes remain blocked unless approved.
- Hermes internal fallback is disabled for Paperclip runs.

Exit criteria:

- MiniMax canary returns successful completion.
- Provider model discovery returns expected Go/Zen model lists.
- No paid fallback route is enabled.

Audibles:

- If MiniMax fails due DNS or transient connection, retry after network check once.
- If MiniMax still fails, keep Paperclip frozen and report provider-blocked.
- If OpenCode Go is healthy but MiniMax is not, continue only with explicit operator approval because it changes the recovery policy.

## Phase 6 - One-Agent Canary Cutover

Purpose: validate the real Paperclip path without changing every agent.

Actions:

1. Choose one low-risk idle `hermes_local` agent with no critical production assignment.
2. Set only that agent's `adapter_config.command` to:

```text
/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes
```

3. Keep `disableFallbackModel: true`.
4. Trigger one controlled Paperclip heartbeat or assignment canary.
5. Verify:

- Hermes command path in run context is the cutover command.
- `source=paperclip` in Hermes state.
- Session id captured before/after.
- Usage fields are readable from `~/.hermes/state.db`.
- No Hermes fallback provider activated.
- The run either completes successfully or blocks for a legitimate task reason, not adapter/runtime failure.

Exit criteria:

- One Paperclip run proves the cutover command works through the real adapter and control plane.

Audibles:

- If canary times out at 900s but shows useful progress, inspect workspace and task logs before retrying.
- If canary fails before child process spawn, inspect Paperclip watchdog/process registry before retrying.
- If canary fails on provider connection, return to Phase 5 and keep freeze in place.
- If canary mutates a shared workspace and fails, do not auto-retry; review workspace receipt first.

## Phase 7 - Clean Stale Execution State

Purpose: stop old blocked/error state from making the restored system look broken.

Actions:

1. Review `24` Hermes agents in `error`.
2. Review `21` stale `in_progress` issues older than 12 hours.
3. For each stale issue:

- Determine whether there was partial workspace mutation.
- Move to `blocked`, `todo`, `done`, or `cancelled` based on evidence.
- Add concise comment with the recovery action and link to the cutover receipt when using the Paperclip API.

4. For stale error agents:

- Reset to idle only after the underlying run/issue state is resolved.
- Leave terminated agents terminated unless they are intentionally being revived.

Exit criteria:

- No stale `in_progress` issue remains without an owner/action.
- Error agents are either reset after proof or left with explicit blockers.

Audibles:

- If a stale issue has unreviewed workspace changes, create or assign a cleanup issue instead of blindly resetting.
- If an error agent owns a credential blocker, leave it blocked and route to the responsible human/operator.

## Phase 8 - Widen The Cutover

Purpose: move from one-agent proof to operational default.

Preferred path:

1. Merge/land the cutover branch into canonical `/Users/mnm/Documents/Github/hermes-agent`.
2. Rebuild/install `/Users/mnm/Documents/Github/hermes-agent/venv/bin/hermes`.
3. Leave Paperclip adapter default command unchanged.

Fast path:

1. Set `adapter_config.command` for all active `hermes_local` agents to:

```text
/Users/mnm/Documents/Github/hermes-agent-upstream-cutover/.venv/bin/hermes
```

2. Keep terminated agents unchanged unless intentionally reviving them.
3. Ensure every active `hermes_local` agent has `disableFallbackModel: true`.

Exit criteria:

- All intended active Hermes agents route to the cutover command.
- Adapter environment check still passes.
- Hermes config includes `plugins.enabled: [portfolio-os]`.

Audibles:

- Prefer the canonical-path merge if downtime is acceptable and full-suite gate is green.
- Use per-agent command override only when a fast reversible canary rollout is needed.
- If more than one agent fails with the same adapter/runtime error, stop widening and rollback command overrides.

## Phase 9 - Staged Unfreeze

Purpose: restore scheduled work without a thundering herd.

Actions:

1. Re-enable one routine family first.
2. Let it complete one full cycle.
3. Run guard receipt.
4. Re-enable the next family only after the prior family is healthy.
5. Final pass:

- Paperclip health `ok`.
- Active runs not stuck.
- Pending wakes draining.
- No new provider connection failure spike.
- No unauthorized paid fallback.
- New Hermes runs use cutover command.

Exit criteria:

- Scheduled systems are operational again and producing successful heartbeat/run receipts.

Audibles:

- If routine runs coalesce into already-stale execution issues, pause that routine family and resolve stale issue state first.
- If provider failures return, freeze only the affected routine family when possible.
- If system-wide failure appears, re-freeze all routine triggers and rollback the Hermes command path.

## Rollback

Rollback is a config/path reversal first, not a data rewrite.

Actions:

1. Freeze Paperclip execution.
2. Revert canary/all-agent `adapter_config.command` overrides, or point the adapter back to:

```text
/Users/mnm/Documents/Github/hermes-agent/venv/bin/hermes
```

3. Remove `portfolio-os` from `plugins.enabled` only if plugin loading itself caused the incident.
4. Restore `~/.hermes/state.db` only if migration/accounting corruption is proven.
5. Re-run a single old-path canary before unfreezing.

Rollback stop condition:

- Do not restore DB from backup while Paperclip or Hermes processes may still be writing.

## Completion Criteria

The recovery is complete only when all are true:

- Full release gate is green or explicitly accepted with documented exceptions.
- Current Hermes execution path is the intended cutover path.
- `portfolio-os` plugin is enabled and visible.
- Paperclip canary through Hermes succeeds.
- MiniMax fresh canary succeeds.
- No active run or wake backlog remains stuck.
- Pre-existing stale/error fleet backlog is documented as non-cutover follow-up and is not blocking scheduler/adapter restoration.
- Routine triggers are re-enabled in controlled stages.
- A final guard receipt shows Paperclip server health, listener state, private/authenticated mode, LaunchAgent cleanup, and no extra listeners.
