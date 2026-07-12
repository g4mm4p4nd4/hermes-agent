# Portfolio-OS execution adapter

This opt-in Hermes plugin validates and executes control-plane-bound
`pos.hermes_task_bundle.v2` bundles. It does not select providers, models,
fallbacks, or release transitions. `pos.hermes_task_bundle.v1` remains readable
for validation and dry-run inspection, but `dispatch` and `resume` return the
nonterminal `validation_only` status and exit nonzero without touching the
target repository.

## Required v2 bindings

An executable bundle must include:

- `governance.execution_authority=paperclip_control_plane`;
- the `profit-flywheel.v2` contract ID, schema version, manifest/schema paths,
  and SHA-256 pins;
- the `provider-policy.v2` ID, revision, schema version, manifest/schema paths,
  and SHA-256 pins;
- one already-resolved route with exact route ID, provider, model, and model
  version;
- correlation, issue, and stage IDs;
- positive `turns`, `context_chars`, `output_chars`, `token_limit`,
  `tool_output_bytes`, `tool_output_lines`, and `tool_output_line_chars`
  budgets, plus `max_tasks` and `max_escalations=0`;
- result, patch-plan, execution-log, and derived journal locations under an
  approved output root.

The invocation must pin the same values through these environment variables:

```text
PAPERCLIP_PROFIT_FLYWHEEL_CONTRACT_PATH
PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_PATH
PAPERCLIP_PROFIT_FLYWHEEL_SHA256
PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_SHA256
PAPERCLIP_PROVIDER_POLICY_PATH
PAPERCLIP_PROVIDER_POLICY_SCHEMA_PATH
PAPERCLIP_PROVIDER_POLICY_SHA256
PAPERCLIP_PROVIDER_POLICY_SCHEMA_SHA256
PAPERCLIP_RESOLVED_ROUTE_ID
PAPERCLIP_RESOLVED_PROVIDER
PAPERCLIP_RESOLVED_MODEL
PAPERCLIP_RESOLVED_MODEL_VERSION
HERMES_PORTFOLIO_OS_OUTPUT_ROOTS
```

The profit-flywheel environment values duplicate compiled trust roots; they do
not define or override them. This plugin release freezes the exact published
bytes below:

| Artifact | SHA-256 |
|---|---|
| `profit-flywheel.v2.json` | `3effdeb311a311bd852cff3d1ce367d4e275c3ce4f0bc4d4adda1c1cb5e6e5f7` |
| `profit-flywheel.v2.schema.json` | `6ac1af81be0de807f51dbba786b73897f114244c1616abee5b3f41a6dbfac09b` |
| `profit-flywheel.run.v2.schema.json` | `ba26611e26941535a29e7faf431e04da3fd05367b2d93e6b8398bebc73872481` |
| `pos.dispatch.v2.schema.json` | `788252407b011f640711f97797f488980bc2b89682a4aa6abe5b5883e162d5e2` |
| `pos.learning_receipt.v2.schema.json` | `e63c3700eae9baa2d75b31d2a222cc7df474d8fbb72165ecddf03d9211ecf267` |
| `pos.next_research_authorization.v1.schema.json` | `8ff5e8b0cad03f4639db23cb994353542493cb6ad3a4c041311b2b374b2bbed7` |
| `paperclip.research_plan.v2.schema.json` | `88faae2962f76f4bf2bfce022cf25b14d9891e836a2b68cea533b3d749f111f4` |
| `stage-work-result.v1.schema.json` | `beff2e8e4d31413329a73e6891d1c9104e004a2a4e621192d39845ff08019fba` |
| `stage-execution.v2.schema.json` | `fb080707e7d65bb17664e494dea765fa4c7018c42a9317d188da8da6be03b6b2` |
| `test-execution-result.v1.schema.json` | `3896d169ef45baae7c19dba9cfb0bc1d2fee18cbc2018d3c734ef23815f896d2` |
| `independent-review-result.v1.schema.json` | `d90769477297810c8536624068fc3af1864d059a6b6d658e9648a0ae53c941af` |
| `execution-golden-vectors.v1.json` | `4ad38f8e0174f1acd0d370837a6c6cdfc61f3bc7f32b7a63c085b973e66eb272` |

The validator hashes the contract, every embedded cross-plane schema, and the
execution golden vectors; parses both manifests; confirms the contract
ID/schema version, and proves the route exists as an exact route in the
provider policy. A missing, substituted, stale, or byte-mismatched pin is a
hard validation failure. Provider-policy hashes remain control-plane revision
pins and must match the exact route manifest supplied for that execution.

## Commands

Validate from the canonical checkout:

```bash
/Users/mnm/Documents/Github/hermes-agent/venv/bin/hermes \
  portfolio-os validate-bundle --bundle /absolute/path/to/bundle.json
```

Replace `validate-bundle` with `dry-run` for non-mutating inspection. `dispatch`
and `resume` emit a `pending` external-adapter handoff receipt and exit nonzero;
they never claim implementation success. `status` exits zero only for a later
Paperclip-authored `succeeded` or `safely_skipped` terminal receipt
(`dry_run_complete` is also terminal for `status`). Every nonterminal state
exits nonzero.

## Execution authority

This plugin never invokes a model, writes a generated repo artifact, runs a
guessed package-manager command, creates a journal, commits, pushes, deploys, or
converts caller-supplied no-op evidence into success. It records the exact
source-byte SHA-256 (plus a canonical-payload SHA-256) and hands the immutable
bundle to Paperclip's `hermes_local` external adapter. Only that issue-bound
adapter run may produce true-final, usage, QA, artifact, and completion
receipts. Implementation stages cannot authorize release; the contract's
`qa -> release` transition remains a control-plane gate.
