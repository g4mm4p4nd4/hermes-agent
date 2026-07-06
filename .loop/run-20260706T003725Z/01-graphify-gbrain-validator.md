# Graphify and GBrain Validator Receipt

Phase: 1
Status: installed-command reality verified
Mode: validate both contract and installed command reality, per Q4.

## Graphify

Command:

```bash
command -v graphify
graphify --help
```

Result:

- executable: `/Users/mnm/.local/bin/graphify`
- help works
- supported commands include `query`, `benchmark`, platform installs, and hooks.

Existing graph:

- Path: `/Users/mnm/Documents/Github/paperclip/graphify-out/graph.json`
- Report: `/Users/mnm/Documents/Github/paperclip/graphify-out/GRAPH_REPORT.md`
- Report date: `2026-06-14`
- Corpus: 23 files, 5,871 words
- Nodes: 342
- Edges: 647
- Communities: 20
- Token cost recorded by report: 83,999 input tokens

Query smoke:

```bash
graphify query "Where does the Paperclip context ledger connect to routine actionability and provider reliability?" --graph graphify-out/graph.json --budget 800
```

Result:

- Query returned relevant context-ledger, provider reliability, routine, and extraction nodes.
- The graph is usable, but it is not current enough to be treated as a complete design authority.

## GBrain

Before install, gstack detection reported:

```json
{
  "gbrain_on_path": false,
  "gbrain_config_exists": false,
  "gbrain_doctor_ok": false,
  "gstack_brain_sync_mode": "off"
}
```

Install path:

```bash
GSTACK_ROOT=/Users/mnm/Documents/Github/gstack /Users/mnm/Documents/Github/gstack/bin/gstack-gbrain-install
gbrain init --pglite --json
```

Result:

- cloned `https://github.com/garrytan/gbrain.git` to `/Users/mnm/gbrain`
- pinned commit: `08b3698e90532b7b66c445e6b1d8cdfe71822802`
- installed version: `gbrain 0.18.2`
- command path: `/Users/mnm/.bun/bin/gbrain`
- engine: local PGLite
- path: `/Users/mnm/.gbrain/brain.pglite`

Current detector:

```json
{
  "gbrain_on_path": true,
  "gbrain_version": "gbrain0.18.2",
  "gbrain_config_exists": true,
  "gbrain_engine": "pglite",
  "gbrain_doctor_ok": true,
  "gstack_brain_sync_mode": "off",
  "gstack_brain_git": false
}
```

Doctor:

- status: `warnings`
- health score: 70
- schema latest: version 24
- connected: true
- pages: 1
- warnings are expected for an empty local brain: no embeddings, no graph coverage, no indexed skills directory.

Smoke:

- A setup smoke page was written.
- `gbrain search "Paperclip flywheel validation"` found it.
- `gbrain get <slug>` returned it.

## Contract Gap

GBrain is now installed and can store receipts. It is not yet wired into Paperclip or Hermes as a required receipt plane, and it is not populated enough to reduce production context usage. The next implementation should add a validator receipt contract that records:

- `graphify` command path and graph freshness
- `gbrain` command path, version, engine, doctor status, and page count
- `scrapegraphai` and `codex-scrapegraph` command paths and dry-run receipts
- per-run evidence fingerprints for VOC, market, feasibility, competitive gap, and council confidence

No MCP registration was performed because this host is Codex, and the setup skill scopes automatic MCP registration to Claude Code unless explicitly requested.
