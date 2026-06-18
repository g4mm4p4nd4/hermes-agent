# Hermes Upstream Cutover Requirements Audit - 2026-06-15

## Scope

This audit checks the requested diligence for upgrading the local
Hermes/Paperclip implementation to latest upstream Hermes.

It does not claim the production cutover has been implemented. It verifies that
the requested mapping, comparison, risk identification, and cutover plan are
captured with current evidence.

## Requirement Audit

| Requirement | Status | Evidence |
| --- | --- | --- |
| Pull/fetch latest upstream Hermes | Complete | `upstream/main` fetched at `ae433634db562e644175d39537ef6b811a381f3f`, described as `v2026.6.5-1033-gae433634d` |
| Compare upstream to current local environment | Complete | Current local install reports `Hermes Agent v0.4.0`; upstream package is `0.16.0`; branch delta is `8` local commits vs `9030` upstream commits |
| Map upstream codebase | Complete | `hermes_upstream_codebase_inventory_2026_06_15.md` sections "Upstream Hermes Map" and "Top-Level Codebase Shape"; `hermes_upstream_cutover_graphs_2026_06_15.md` section "Upstream Runtime Map" |
| Map codebase differences | Complete | `hermes_upstream_codebase_inventory_2026_06_15.md` sections "Top-Level Codebase Shape" and "Delta Classification"; matrix file surfaces classify local/upstream differences |
| Map local installation including upgrades/custom changes | Complete | `hermes_upstream_codebase_inventory_2026_06_15.md` sections "Local Hermes Fork Map", "Local Portfolio-OS Adapter Map", and "External Paperclip Adapter Map" |
| Compare what we have and do not have | Complete | `hermes_upstream_cutover_matrix_2026_06_15.json` has per-surface `local_state`, `upstream_state`, `what_we_gain`, and `what_we_could_lose`; assessment has "Local Commits To Preserve Or Retire" |
| Identify areas that can break | Complete | Matrix classifications include `must_port`, `must_preserve`, `must_add_or_verify`, `preserve_as_paperclip_guard`, and `must_preserve_and_test`; inventory has "Areas That Look Like Upgrades But Can Lose Behavior" |
| Red-team missing production cutover gates | Complete | `hermes_upstream_cutover_red_team_2026_06_15.md` adds P0/P1 blocker ledger for CLI compatibility, direct merge conflicts, live Paperclip inventory, paid-provider denial, state migration, plugin enablement, drain/freeze, and rollback |
| Identify areas that are upgrades | Complete | Assessment "Upstream Improvements Worth Taking"; inventory "Upstream areas that are real upgrades"; matrix classifications `replace_local_with_upstream` and `upgrade_with_policy_guard` |
| Identify areas likely not impacted | Complete | Inventory "Delta Classification" marks gateway/platform adapters, cockpit plugin config, target-result schema, and skill surfaces as isolated/not impacted only when disabled or ported deliberately |
| Detail potential losses inside apparent upgrades | Complete | Inventory explicitly covers `fallback_providers`, plugin CLI registration, provider profiles, packaging, ACP, and output/token handling as upgrade-looking surfaces with possible losses |
| Preserve fallback routing and model inference behavior | Complete as plan, not implemented | Matrix and inventory require MiniMax-first policy, OpenCode Go/Zen routing, qwen replacement tests, and paid-provider hard gates |
| Preserve OpenCode Go and MiniMax support | Complete as plan, not implemented | Upstream provider profiles are identified as preferred core; external adapter tests prove current OpenCode Go/Zen expectations |
| Preserve hard gate for OpenAI, Claude, Gemini | Complete as plan, not implemented | Matrix requires paid-provider escalation denial without approval; inventory calls this out as the central fallback risk |
| Pause Paperclip/Hermes adapter when inference fails | Complete as plan, not implemented | Matrix surface `adapter_pause_on_failure` requires blocked result plus pause signal; inventory includes it as not upstream and must preserve/add |
| Validate inference availability before adapter fires | Partially complete today; remaining cutover requirement defined | External adapter currently has `testEnvironment()` and completion probe; Python Portfolio plugin cutover must add pre-dispatch probe before target mutation |
| Include external Paperclip adapter | Complete | Inventory and matrix include `/Users/mnm/Documents/Github/hermes-paperclip-adapter` and cockpit `adapter-plugins.json`; `npm test` passed |
| Produce a safe cutover plan | Complete | Assessment "Recommended Cutover Plan"; inventory "Safe Cutover Plan"; matrix `recommended_cutover_summary` |
| Validate current baseline tests | Complete | Hermes focused tests: `46 passed`; external adapter tests: `29 passed`; JSON validation and `git diff --check` clean |

## Current Evidence Files

- `docs/portfolio_os/hermes_upstream_cutover_assessment_2026_06_15.md`
- `docs/portfolio_os/hermes_upstream_cutover_graphs_2026_06_15.md`
- `docs/portfolio_os/hermes_upstream_cutover_matrix_2026_06_15.json`
- `docs/portfolio_os/hermes_upstream_codebase_inventory_2026_06_15.md`
- `docs/portfolio_os/hermes_upstream_cutover_requirements_audit_2026_06_15.md`
- `docs/portfolio_os/hermes_upstream_cutover_red_team_2026_06_15.md`

## Test Evidence

Hermes focused baseline:

```bash
source venv/bin/activate && python -m pytest tests/test_runtime_provider_resolution.py tests/test_portfolio_os_adapter.py -q
```

Result:

```text
46 passed
```

External Paperclip adapter:

```bash
npm test
```

Run from:

```text
/Users/mnm/Documents/Github/hermes-paperclip-adapter
```

Result:

```text
29 passed
```

Document validation:

```bash
source venv/bin/activate && python -m json.tool docs/portfolio_os/hermes_upstream_cutover_matrix_2026_06_15.json >/dev/null
git diff --check
```

Result:

```text
both passed with no output
```

## Remaining Work For Actual Cutover

The diligence and plan are complete. The production cutover itself remains
future implementation work:

1. Branch from `upstream/main`.
2. Build a fresh upstream environment.
3. Port the Python Portfolio-OS adapter as an upstream plugin.
4. Preserve or replace `--disable-fallback-model` for the external adapter.
5. Add Paperclip-specific MiniMax-first hard-stop tests.
6. Add Python adapter/plugin inference preflight before target repo mutation.
7. Update the external adapter command path after its tests and
   `testEnvironment()` pass.
8. Prove upstream `state.db` migration and external-adapter usage accounting on
   a copied production database.
9. Produce live Paperclip inventory, drain/freeze receipt, and rollback
   rehearsal evidence.
10. Run full upstream/Paperclip/cockpit canary before switching production.
