"""Compatibility entrypoint for the historical ``portfolio_os_adapter.cli``."""

from plugins.portfolio_os.cli import *  # noqa: F401,F403
from plugins.portfolio_os.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
