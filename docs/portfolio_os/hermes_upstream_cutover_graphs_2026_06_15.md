# Hermes Upstream Cutover Graphs - 2026-06-15

## Scope

This file maps the current Hermes Agent fork, the fetched upstream Hermes
runtime, and the Paperclip/Portfolio-OS adapter cutover path.

Native Graphify note: the installed `graphify` binary on this host currently
exposes query/install/hook commands only, not the full extraction pipeline in
the Graphify skill reference. These maps are therefore Graphify-style manual
maps built from fetched git state, direct file reads, and current test output.
No synthetic edge below is presented as native Graphify output.

## Evidence Coordinates

- Local checkout: `main` at `8bba7a17c`.
- Upstream checkout: `upstream/main` at `ae433634d`.
- Branch delta: `8` local commits ahead, `9030` upstream commits behind.
- Local package version: `0.4.0`.
- Upstream package version: `0.16.0`.
- Focused local tests: `tests/test_runtime_provider_resolution.py` and
  `tests/test_portfolio_os_adapter.py` passed with `46 passed`.
- Local adapter command: `./bin/hermes portfolio-os`.
- Upstream deletion forecast: `HEAD..upstream/main` deletes `bin/hermes`,
  `portfolio_os_adapter/*`, and existing `docs/portfolio_os/*` unless they are
  explicitly reintroduced.

## Current Runtime And Adapter Map

```mermaid
flowchart TD
    paperclip["Paperclip cockpit and Portfolio-OS scheduler"]
    bundle["pos.hermes_task_bundle.v1 JSON bundle"]
    wrapper["./bin/hermes wrapper"]
    cli["portfolio_os_adapter.cli"]
    contract["portfolio_os_adapter.contract"]
    runtime["portfolio_os_adapter.runtime"]
    target["target repo under allowed roots"]
    qa["target repo QA command"]
    gitops["branch, add, commit, optional push"]
    secrets["secret-like diff scan"]
    result["data/hermes_results/<run_id>.json"]
    dryrun["data/hermes_status/<run_id>.dry_run.json"]
    log["execution_log_path"]
    paperclip_ids["paperclip execution id, issue ids, gstack artifacts"]

    paperclip --> bundle
    bundle --> wrapper
    wrapper --> cli
    cli --> contract
    contract -->|"schema, root, safety, Internet Pipes"| runtime
    runtime --> target
    runtime --> qa
    runtime --> secrets
    secrets --> gitops
    gitops --> result
    runtime --> dryrun
    runtime --> log
    result --> paperclip_ids
    dryrun --> paperclip
    result --> paperclip
```

Meaning: the current adapter is a safety and artifact boundary, not just a
terminal shortcut. The cutover must preserve the bundle contract, allowed-root
guard, Internet Pipes readiness checks, push policy, forbidden-operation checks,
secrets scan, QA result capture, and Paperclip result schema.

## Current Local Patch Map

```mermaid
flowchart LR
    fork["Local Hermes fork 0.4.0"]
    provider_meta["OpenCode provider metadata"]
    fallback_disable["fallback disable hard stop"]
    pos_adapter["Portfolio-OS adapter"]
    opencode_alias["OpenCode Go Qwen alias patch"]
    acp_auth["ACP auth schema compatibility"]
    output_budget["compact output budget contract"]
    stale_api_mode["uncommitted stale api_mode guard"]

    fork --> provider_meta
    fork --> fallback_disable
    fork --> pos_adapter
    fork --> opencode_alias
    fork --> acp_auth
    fork --> output_budget
    fork --> stale_api_mode
```

Decision overlay:

- Replace with upstream: OpenCode provider metadata, OpenCode Go model routing,
  ACP auth compatibility, stale `api_mode` guard.
- Preserve and port: Portfolio-OS adapter, Internet Pipes bundle contract,
  Paperclip result artifacts, fallback hard-stop policy.
- Decide placement: compact output budget contract. Global behavior is not
  present upstream; Paperclip-local output shaping is lower risk than changing
  upstream's global conversation loop.

## Upstream Runtime Map

```mermaid
flowchart TD
    upstream["upstream/main 0.16.0"]
    plugins["hermes_cli.plugins PluginManager"]
    provider_plugins["plugins/model-providers/*"]
    minimax["MiniMax, MiniMax CN, MiniMax OAuth profiles"]
    opencode["OpenCode Zen and OpenCode Go profiles"]
    runtime_provider["hermes_cli.runtime_provider"]
    model_modes["hermes_cli.models model api_mode inference"]
    prompt_cache["agent.agent_runtime_helpers prompt cache policy"]
    fallback["fallback_providers chain"]
    acp["acp_adapter auth/session/tooling"]
    gateway["gateway and platform plugin surfaces"]
    packaging["exact pins, uv.lock, Python >=3.11,<3.14"]
    cli_plugins["register_cli_command"]

    upstream --> plugins
    upstream --> provider_plugins
    provider_plugins --> minimax
    provider_plugins --> opencode
    provider_plugins --> runtime_provider
    runtime_provider --> model_modes
    runtime_provider --> prompt_cache
    runtime_provider --> fallback
    upstream --> acp
    upstream --> gateway
    upstream --> packaging
    plugins --> cli_plugins
```

Meaning: upstream has stronger provider infrastructure than the fork. The safe
strategy is to adopt upstream core and re-port Paperclip as an upstream-style
plugin instead of carrying an old core fork.

## Provider And Fallback Risk Map

```mermaid
flowchart TD
    dispatch["Paperclip Hermes dispatch request"]
    preflight["Paperclip inference preflight"]
    primary["configured primary provider or model"]
    opencode_go["OpenCode Go profile"]
    minimax["MiniMax recovery lane"]
    block["blocked result and adapter pause"]
    paid["OpenAI, Claude, Gemini, other paid tiers"]
    approval["explicit Paperclip approval flag"]
    upstream_chain["upstream fallback_providers chain"]

    dispatch --> preflight
    preflight -->|"valid creds, valid api_mode, model reachable"| primary
    primary --> opencode_go
    primary -->|"recoverable failure"| minimax
    minimax -->|"success"| dispatch
    minimax -->|"unavailable or exhausted"| block
    upstream_chain --> minimax
    upstream_chain --> paid
    paid --> approval
    approval --> paid
    paid -. "must be denied without approval" .-> block
```

Required cutover behavior: upstream may support broad fallback chains, but the
Paperclip adapter must impose a hard boundary. After MiniMax exhaustion the
adapter should write an auditable blocked result and pause the Paperclip/Hermes
execution lane rather than continuing into OpenAI, Claude, Gemini, or another
paid provider without explicit approval.

## Adapter Re-Home Map

```mermaid
flowchart TD
    old_wrapper["old ./bin/hermes portfolio-os"]
    old_package["portfolio_os_adapter package"]
    upstream_cli["upstream hermes_cli.main"]
    plugin_manager["PluginManager discovers enabled plugins"]
    paperclip_plugin["plugins/paperclip_portfolio_os"]
    register_cli["ctx.register_cli_command(name='portfolio-os')"]
    same_commands["validate-bundle, dry-run, dispatch, status, resume"]
    contract_tests["adapter contract tests"]
    fallback_tests["MiniMax hard-stop fallback tests"]
    live_canary["Paperclip live canary"]

    old_wrapper --> old_package
    upstream_cli --> plugin_manager
    plugin_manager --> paperclip_plugin
    paperclip_plugin --> register_cli
    register_cli --> same_commands
    same_commands --> contract_tests
    same_commands --> fallback_tests
    fallback_tests --> live_canary
    contract_tests --> live_canary
```

Porting target: create a Paperclip/Portfolio-OS plugin that registers the same
operator command surface through `ctx.register_cli_command`. The plugin must be
enabled or bundled explicitly because upstream standalone plugins are opt-in by
default.

## External Paperclip Adapter Map

```mermaid
flowchart TD
    cockpit["Paperclip cockpit adapter manager"]
    registration["adapter-plugins.json hermes_local"]
    adapter["/Users/mnm/Documents/Github/hermes-paperclip-adapter"]
    models["OpenCode Go/Zen live model discovery"]
    envcheck["testEnvironment()"]
    probe["selected provider completion probe"]
    routing["model/provider routing normalization"]
    disable["--disable-fallback-model + HERMES_DISABLE_FALLBACK_MODEL=1"]
    hermes["Hermes CLI command path"]
    usage["state.db usage accounting"]

    cockpit --> registration
    registration --> adapter
    adapter --> models
    adapter --> envcheck
    envcheck --> probe
    adapter --> routing
    routing --> disable
    disable --> hermes
    adapter --> usage
```

Meaning: the Paperclip cutover has an external JavaScript adapter as well as
the Python Portfolio-OS adapter inside this repo. Upstream Hermes does not own
that adapter. The new Hermes environment must either preserve its current CLI
contract (`hermes chat`, `--disable-fallback-model`, provider/model flags) or
the adapter must be updated and tested before the cockpit command path is
switched.

## Cutover Validation Graph

```mermaid
flowchart LR
    branch["new branch from upstream/main"]
    env["fresh upstream env via uv or upstream install path"]
    port["port Paperclip plugin"]
    unit["unit and contract tests"]
    provider["provider routing tests"]
    fallback["fallback hard-stop tests"]
    external["external adapter npm test"]
    acp["ACP smoke tests"]
    adapter["adapter dry-run and dispatch tests"]
    cockpit["Paperclip guard and canary"]
    switch["production path switch"]
    rollback["rollback to current main and venv"]

    branch --> env
    env --> port
    port --> unit
    unit --> provider
    provider --> fallback
    fallback --> external
    external --> acp
    acp --> adapter
    adapter --> cockpit
    cockpit --> switch
    switch --> rollback
```

Hard stops:

- `hermes portfolio-os` is missing.
- A valid `pos.hermes_task_bundle.v1` fixture fails validation.
- Any launch bundle with missing Internet Pipes stations dispatches.
- MiniMax exhaustion continues into OpenAI, Claude, Gemini, or another paid
  provider without explicit approval.
- Result JSON or execution log schema differs from Paperclip's expected
  contract.
- Paperclip cockpit guard fails after the path switch.
