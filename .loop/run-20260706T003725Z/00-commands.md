# Phase 0 Command Baselines

Collected during corrected cross-repo Phase 0.

## Live Health

```bash
curl -sS http://127.0.0.1:3100/api/health
```

Result: pass. Returned Paperclip `status=ok`, `version=0.3.1`, authenticated private deployment, auth ready.

```bash
lsof -nP -iTCP:3100 -sTCP:LISTEN
lsof -nP -iTCP:3101 -sTCP:LISTEN
```

Result: `3100` has Paperclip server listener; `3101` has no listener.

## Portfolio OS

```bash
./bin/pos --help
./bin/pos flywheel-status --help
./bin/pos health --help
```

Result: pass. Command surface includes research, intake, council, dispatch, Hermes/GStack integration, flywheel status, self-heal, sync, health, and repo-cache commands.

Not run in Phase 0:

```bash
./bin/startup_worktree.sh
./bin/pos sync-automations --check
./bin/pos health
```

Reason: `portfolio-os` has 394 dirty paths. Discovery should not run truth-plane writers or checks that may mutate/report over a dirty artifact baseline before preservation/classification.

## Paperclip

```bash
pnpm --filter @paperclipai/adapter-utils typecheck
```

Result: pass.

```bash
pnpm --filter @paperclipai/server exec vitest run src/__tests__/work-products.test.ts src/__tests__/context-ledger-service.test.ts --testTimeout=15000
```

Result: pass. `2` test files, `12` tests passed.

Package scripts observed include `typecheck`, `test:run`, `ops:dirty-session-preservation`, and `ops:portfolio-existing-venture-gate`.

## Hermes Agent

```bash
source venv/bin/activate && hermes --help
source venv/bin/activate && hermes chat --help
```

Result: pass. `hermes chat` supports `--provider`, `--quiet`, `--resume`, `--continue`, `--worktree`, `--pass-session-id`, `--disable-fallback-model`, and `--source`.

Earlier Hermes-only Phase 0 full baseline retained:

```bash
source venv/bin/activate && OPENROUTER_API_KEY="" OPENAI_API_KEY="" NOUS_API_KEY="" python -m pytest tests/ -q --ignore=tests/integration --tb=short -n auto
```

Result: pass. `6351 passed, 164 skipped, 110 warnings in 65.87s`.

Blocked local docs/Nix baselines from earlier Phase 0:

- `cd website && npm run lint:diagrams` failed locally because `ascii-guard` was not on PATH.
- `nix flake show --json` could not run because `nix` was not available.

## Hermes Paperclip Adapter

```bash
npm test
```

Result: pass. `39` tests passed. Coverage included Hermes command contract export, OpenCode model discovery, unsupported flag skipping, Paperclip API auth env redaction, session params, compact context, final response recovery, usage accounting, OpenCode routing, Internet Pipes prompt projection, session-resume suppression, tool-output budgets, and adaptive skill preloading.

Package script:

```json
{"test":"node --test"}
```

## GStack

```bash
bun run automation:pos-smoke
```

Result: pass. `379` tests passed across `test/pos-artifact.test.ts` and `test/gen-skill-docs.test.ts`.

Relevant output: POS artifact resolver covered dispatch/selection/Hermes bundle evidence, QA, patch-plan, and bounded retrieval context; generated SKILL.md freshness checks passed.

## Graphify

```bash
graphify --help
```

Result: pass. Command surface includes `query`, `benchmark`, hook install/uninstall/status, and platform installs for Codex/OpenCode/OpenClaw/Factory Droid.

Not run:

```bash
graphify <full build or large repo graph>
```

Reason: the Graphify skill guidance requires narrowing before large repos; current task is Phase 0 discovery and existing context packs/graph outputs are safer.

## ScrapeGraphAI

```bash
scrapegraphai --help
codex-scrapegraph --help
```

Result: pass. Command surface supports `--source`, `--prompt`, `--mode`, `--model`, `--model-tokens`, `--api-key-env`, `--output`, `--output-dir`, and `--dry-run`.

```bash
scrapegraphai --source README.md --prompt 'Extract the repository title and one sentence purpose.' --dry-run --output /tmp/scrapegraphai-phase0-dry-run.json
```

Result: pass. Returned `status: OK`, `mode: smart`, `model: openai/gpt-4o-mini`, `dry_run: true`, `source_count: 1`, no LLM call.

## Internet Pipes Knowledgebase

Read-only docs inspected:

- `README.md`
- `integrations/scrapegraphai/README.md`
- `docs/entrepreneur_opportunity_prompt.md`

Not run:

```bash
uv run pytest
```

Reason: not needed for Phase 0 after ScrapeGraphAI dry-run and doc contract validation; reserve for a Phase 1/2 item if the Internet Pipes package itself becomes a touched implementation surface.
