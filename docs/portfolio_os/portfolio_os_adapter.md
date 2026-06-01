# Portfolio-OS Adapter Runtime

The Portfolio-OS adapter is a sidecar runtime. It does not replace Hermes chat, gateway, ACP, Honcho, approval, or skill behavior.

## Runtime Behavior

- `validate-bundle` parses and validates `pos.hermes_task_bundle.v1`.
- `dry-run` resolves the target repo and writes a dry-run status artifact without mutation.
- `dispatch` creates or switches to the configured working branch, executes safe task types, runs available tests, commits changed files, optionally pushes, and writes a result artifact.
- `status` reads result or dry-run artifacts.
- `resume` reopens the saved run bundle and continues dispatch.

When a task cannot be safely implemented as code, Hermes creates the corresponding docs-based validation asset. That keeps validation sprint execution moving without guessing framework-specific changes.
