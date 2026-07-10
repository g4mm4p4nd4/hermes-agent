"""Portfolio-OS bundled plugin.

This plugin carries the Paperclip/Portfolio-OS task-bundle adapter as a
standalone, opt-in Hermes CLI command:

    hermes portfolio-os validate-bundle --bundle <path>

The implementation intentionally lives at the plugin edge so upstream Hermes can
keep its core CLI and agent loop generic while Paperclip keeps the execution
contract it already depends on.
"""

from __future__ import annotations

from .cli import main as portfolio_os_command
from .cli import register_cli


def register(ctx) -> None:
    ctx.register_cli_command(
        name="portfolio-os",
        help="Portfolio-OS task bundle adapter",
        setup_fn=register_cli,
        handler_fn=portfolio_os_command,
        description=(
            "Validate, dry-run, dispatch, inspect, and resume "
            "pos.hermes_task_bundle.v1 execution bundles."
        ),
    )
