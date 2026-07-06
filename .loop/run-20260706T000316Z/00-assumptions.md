# Phase 0 Assumptions

Run id: `20260706T000316Z`

1. Target repo defaulted to the current checkout, `/Users/mnm/Documents/Github/hermes-agent`, because the latest instruction provided a general loop protocol and did not name another repository.

2. Review mode is active because the loop default says `AUTONOMY=review` unless overridden in the project map, and no prior `.loop/project-map.md` existed in this repo.

3. Phase 0 may write `.loop/` artifacts but must not start object-level diagnosis/fixing until the operator confirms `00-criteria.md`.

4. The local contributor environment should use `venv` because `AGENTS.md` says to activate `venv/bin/activate`; CI creates `.venv`, but this checkout has `venv` and no `.venv`.

5. Website lint/build checks are relevant only for website/docs-site footprints unless a future task explicitly broadens the scope.

6. Nix checks are relevant for Nix and core package footprints named by `.github/workflows/nix.yml`, but cannot be executed locally until `nix` is installed.

7. The checkout being ahead of `origin/main` by two commits is treated as a merge/push safety constraint, not as a blocker for local Phase 0 artifact generation.
