# Hermes Upstream Cutover Assessment - 2026-06-15

## Executive Recommendation

Do not merge `upstream/main` directly into the current `main`. Treat this as a
new-upstream rebase/cutover project.

The local Hermes runtime is `0.4.0` on `8bba7a17c`, with eight committed fork
patches and three uncommitted runtime-provider hardening edits. Fetched upstream
is `ae433634d`, version `0.16.0`, described as `v2026.6.5-1033-gae433634d`.
The branch delta is 8 local commits versus 9030 upstream commits.

Most provider/runtime patches should be replaced by upstream implementations.
The Portfolio-OS/Paperclip adapter is not present upstream and must be preserved
explicitly, preferably as an upstream-style plugin CLI command rather than as a
core package patch.

## Baseline Evidence

- Local branch: `main` at `8bba7a17c`, tracking `origin/main`.
- Upstream branch: `upstream/main` at `ae433634d`.
- Shared merge base: `bdccdd67a1c3f16aa4d15f700a9615bbc4d141f7`.
- Local environment: `Hermes Agent v0.4.0 (2026.3.23)`, Python `3.11.15`.
- Upstream package version: `0.16.0`, Python requirement `>=3.11,<3.14`.
- Current runnable adapter entry: `./bin/hermes portfolio-os ...`.
- Installed console script: `/Users/mnm/.local/bin/hermes`; it does not expose
  `portfolio-os` in the observed help output.
- External Paperclip adapter: `/Users/mnm/Documents/Github/hermes-paperclip-adapter`,
  registered in the cockpit as `hermes_local` version `0.1.0`.
- Focused current tests passed:
  `python -m pytest tests/test_runtime_provider_resolution.py tests/test_portfolio_os_adapter.py -q`
  returned `46 passed`.
- The local `venv` has no `pip` module, so package-management inspection via
  `python -m pip show hermes-agent` is unavailable in this environment.

## Local Commits To Preserve Or Retire

1. `cb1dd7e30` - OpenCode provider metadata and context guidance.
   Upstream has provider plugins for OpenCode Zen and Go, model-specific API
   mode routing, curated models, and prompt-cache support for Qwen/Alibaba
   family traffic. Prefer upstream.

2. `4c100e48f` - fallback model disable control.
   Upstream has a richer `fallback_providers` chain and `hermes fallback`
   manager, but no observed equivalent of the local per-invocation
   `--disable-fallback-model` / env hard stop. Preserve the hard-stop policy
   for Paperclip runs if fallback beyond MiniMax remains forbidden.

3. `af7eb5c76`, `167e6f3ce`, `8bba7a17c` - Portfolio-OS adapter, namespace
   acceptance, Internet Pipes bundle contract.
   Upstream does not contain this adapter. Preserve it, but re-home it as a
   plugin CLI command if possible.

4. `9f46017ca` - OpenCode Go Qwen OA-compatible alias handling.
   Upstream has broader OpenCode Go model routing and Qwen cache-control logic.
   Prefer upstream, then add a focused regression only if the exact local alias
   is still missing.

5. `6be74cea6` - ACP auth method schema rename.
   Upstream supersedes this with `acp_adapter/auth.py::build_auth_methods()`,
   terminal setup auth, configured-provider auth, and tests for both configured
   and unconfigured ACP startup.

6. `f0a1f4f12` - output budgets and compact output contract.
   Upstream has significant `max_output_tokens`, overflow retry, and provider
   cap handling. It does not carry the local compact-response contract
   (`output.max_sentences`, `output.max_chars`, compacted suffix). Decide
   whether that behavior is still wanted globally or should move to the
   Paperclip/Portfolio adapter boundary only.

7. Uncommitted local runtime-provider patch - ignore stale `api_mode` when the
   configured provider differs from the requested provider.
   Upstream has a better general implementation:
   `hermes_cli/runtime_provider.py::_provider_supports_explicit_api_mode()`.
   Use upstream's version and keep or port a MiniMax-specific regression test.

## Upstream Improvements Worth Taking

- Provider system moved toward plugin profiles under `plugins/model-providers`.
- MiniMax, MiniMax OAuth, MiniMax CN, OpenCode Zen, and OpenCode Go are
  first-class provider profiles.
- Runtime provider resolution now gates stale `api_mode` and `base_url` by
  configured provider, avoiding cross-provider leakage.
- `fallback_providers` replaces single `fallback_model` with ordered failover
  while retaining legacy compatibility.
- Subagents and cron now inherit fallback chains upstream.
- ACP support is much broader, including terminal setup auth and richer session
  capability handling.
- Plugin CLI command registration allows a Paperclip/Portfolio integration to
  register `hermes portfolio-os` without editing the core CLI parser.
- Packaging is much stricter: exact pins, `uv.lock`, Python `<3.14`, plugin
  package data, and lazy extras for high-risk optional dependencies.
- Gateway/platform architecture has moved toward plugin adapters.

## Caveats And Cutover Risks

- Direct merge risk is high. The upstream delta touches 5069 files with roughly
  1.5M insertions and 97K deletions against current HEAD.
- The current adapter package, docs, and wrapper are deleted by
  `HEAD..upstream/main` unless explicitly reintroduced.
- Current Paperclip policy requires MiniMax-first recovery and a hard stop after
  MiniMax exhaustion. Upstream fallback chains can continue into later providers
  unless configured and guarded.
- The local `--disable-fallback-model` behavior does not appear to exist
  upstream. Paperclip execution should get an explicit no-paid-tier escalation
  guard.
- The local compact output contract is not upstream. If Paperclip workflows rely
  on compact artifacts, port it as adapter-local output shaping instead of
  changing global Hermes output behavior.
- The external Paperclip adapter depends on the current Hermes CLI contract:
  `hermes chat`, provider/model flags, `--disable-fallback-model`,
  `HERMES_DISABLE_FALLBACK_MODEL=1`, Hermes session ids, and `state.db` usage
  accounting. Upstream does not own that adapter, so it must be tested and
  re-pointed deliberately.
- Upstream packaging relies on `uv.lock` and stricter exact pins. The current
  local `venv` lacks `pip`, so the cutover should use upstream's documented
  `uv`/script path rather than trying to mutate the old environment in place.
- Upstream plugin loading is opt-in for user/project plugins. A Paperclip plugin
  must be bundled, explicitly enabled, or installed/configured during rollout.
- Upstream has many new desktop, TUI, dashboard, gateway, and service surfaces.
  Paperclip guard validation must cover process ownership and ports so a new
  Hermes gateway/dashboard does not collide with the existing Paperclip cockpit.

## Red-Team Hard Stops Added After Review

The adversarial review is captured in
`docs/portfolio_os/hermes_upstream_cutover_red_team_2026_06_15.md`. It adds
the following production gates to the cutover package:

- Do not point Paperclip at upstream Hermes until
  `--disable-fallback-model` is preserved or replaced with a proven equivalent.
- Do not direct-merge `upstream/main`; the merge forecast conflicts in CLI,
  gateway, provider, session-state, package, ACP, and docs surfaces.
- Do not switch production without a live Paperclip inventory covering
  `hermes_local` adapters, active/queued runs, heartbeats, scheduled wakes,
  provider approvals, and command paths.
- Do not migrate the live Hermes `state.db` in place; prove upstream schema
  migration and external-adapter usage accounting on a copy first.
- Do not rely on generic upstream `fallback_providers` for Paperclip until tests
  prove MiniMax exhaustion writes a blocked artifact and invokes no denied paid
  provider without approval.

## Recommended Cutover Plan

1. Create a new branch from `upstream/main`, for example
   `codex/hermes-upstream-paperclip-cutover`.

2. Rebuild the environment from upstream rules, not the old `venv`:
   use upstream's preferred dependency workflow and keep Python within
   `>=3.11,<3.14`.

3. Port only the local changes that remain necessary:
   - convert `portfolio_os_adapter` into an upstream-style plugin that registers
     the `portfolio-os` CLI command with `ctx.register_cli_command`;
   - keep the existing command surface:
     `validate-bundle`, `dry-run`, `dispatch`, `status`, `resume`;
   - preserve Internet Pipes validation, allowed-root checks, forbidden
     operations, result artifact schema, execution log schema, Paperclip ids,
     and GStack artifact passthrough;
   - preserve `pos.hermes_task_bundle.v1` and the `portfolio-os` namespace;
   - add or retain packaging metadata so the plugin ships in editable and wheel
     installs.

4. Preserve the external Paperclip adapter contract:
   - keep adapter type `hermes_local`;
   - keep or replace `--disable-fallback-model` with an equivalent hard gate;
   - keep OpenCode Go/Zen model discovery and required-lane checks;
   - keep the `qwen3.7-max` to `deepseek-v4-pro` Paperclip routing replacement
     until live upstream/OpenCode evidence proves the original model safe;
   - update the configured Hermes command path only after `npm test` and
     `testEnvironment()` pass against the new environment.

5. Replace local provider patches with upstream equivalents:
   - remove the local `_model_config_api_mode_applies` helper;
   - rely on `_provider_supports_explicit_api_mode`;
   - port the MiniMax stale-api-mode regression test if upstream does not cover
     that exact case;
   - rely on upstream OpenCode provider profiles and `opencode_model_api_mode`;
   - verify OpenCode Go Qwen alias behavior with a focused test.

6. Implement a Paperclip-safe fallback policy:
   - configure fallback chain as MiniMax first;
   - prevent automatic escalation to OpenAI, Claude, Gemini, or other paid tiers
     unless a Paperclip approval flag is present;
   - add tests proving MiniMax exhaustion stops the run and produces an
     auditable blocker instead of continuing into paid providers;
   - document the exact config keys Paperclip sets.

7. Decide output policy:
   - if compact output is only needed for Paperclip artifacts, apply it inside
     the Portfolio/Paperclip plugin result writer;
   - if it is still desired globally, port the config keys and tests into
     upstream's current conversation-loop/finalizer architecture.

8. Validate in layers:
   - upstream smoke/import tests;
   - runtime provider tests;
   - plugin CLI registration tests;
   - Portfolio-OS adapter contract tests;
   - external adapter `npm test`;
   - ACP auth tests;
   - fallback-chain hard-stop tests;
   - full non-integration test suite before any production switch.

9. Run a live Paperclip canary:
   - validate a real `pos.hermes_task_bundle.v1` fixture;
   - run dry-run and inspect `data/hermes_status`;
   - dispatch against a disposable target repo first;
   - dispatch against a real low-risk target with push disabled;
   - confirm result/log artifacts exactly match the current Paperclip contract;
   - confirm no unauthorized provider spend paths were exercised.

10. Cut over operationally:
   - snapshot the current Hermes checkout and Paperclip config;
   - stop Hermes/Paperclip jobs that may dispatch bundles;
   - install or point Paperclip to the new branch/environment;
   - run the Paperclip cockpit guard;
   - run the adapter canary;
   - re-enable scheduled Paperclip dispatch only after guard and canary are both
     green.

11. Rollback plan:
    - keep current `main` and `venv` untouched until the new branch proves out;
    - keep Paperclip configured to switch back to the old `./bin/hermes` path;
    - treat any provider escalation, missing result artifact, wrong bundle
      schema, or Paperclip guard failure as rollback conditions.

## Practical Bottom Line

Cut over to upstream for Hermes core, provider runtime, ACP, packaging, and
fallback infrastructure. Do not cut over the Paperclip/Portfolio adapter by
deleting it or hoping upstream covers it. Re-port it deliberately as a plugin
CLI integration and add Paperclip-specific tests around bundle safety,
Internet Pipes readiness, result artifacts, and MiniMax-first hard-stop
behavior.
