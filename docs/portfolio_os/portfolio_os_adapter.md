# Portfolio-OS Adapter Runtime

The Portfolio-OS adapter is a sidecar runtime. It does not replace Hermes chat, gateway, ACP, Honcho, approval, or skill behavior.

## Runtime Behavior

- `validate-bundle` parses and validates `pos.hermes_task_bundle.v1`.
- `dry-run` resolves the target repo and writes a dry-run status artifact without mutation.
- `dispatch` creates or switches to the configured working branch, executes safe task types, runs available tests, commits changed files, optionally pushes, and writes a result artifact.
- `status` reads result or dry-run artifacts.
- `resume` reopens the saved run bundle and continues dispatch.

The adapter treats Internet Pipes completeness as part of the execution contract. Launch bundles are rejected unless the bundle is `alpha_ready` or `factory_ready` with no missing stations. Validation and backfill bundles can still run while stations are missing, and Hermes preserves the station score, readiness, missing stations, and recommendations in dry-run, result, log, and README artifacts.

When a task cannot be safely implemented as code, Hermes creates the corresponding docs-based validation asset. That keeps validation sprint execution moving without guessing framework-specific changes.
