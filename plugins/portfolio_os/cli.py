from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runtime import (
    dispatch_bundle,
    dry_run_bundle,
    resume_run,
    status_for_run,
    validate_bundle_file,
)


def _add_commands(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-bundle", help="Validate a pos.hermes_task_bundle.v1 file")
    validate.add_argument("--bundle", required=True)
    validate.set_defaults(func=cmd_validate_bundle)
    dry_run = sub.add_parser("dry-run", help="Plan bundle execution without mutating the target repo")
    dry_run.add_argument("--bundle", required=True)
    dry_run.set_defaults(func=cmd_dry_run)
    dispatch = sub.add_parser("dispatch", help="Execute a bundle against the selected target repo")
    dispatch.add_argument("--bundle", required=True)
    dispatch.set_defaults(func=cmd_dispatch)
    status = sub.add_parser("status", help="Show run status")
    status.add_argument("--run-id", required=True)
    status.add_argument("--portfolio-os-root", default="/Users/mnm/Documents/Github/portfolio-os")
    status.set_defaults(func=cmd_status)
    resume = sub.add_parser("resume", help="Resume a run from its stored bundle")
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--portfolio-os-root", default="/Users/mnm/Documents/Github/portfolio-os")
    resume.set_defaults(func=cmd_resume)


def register_cli(parser: argparse.ArgumentParser) -> None:
    parser.description = "Portfolio-OS task bundle execution adapter."
    _add_commands(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes portfolio-os")
    _add_commands(parser)
    return parser


def cmd_validate_bundle(args: argparse.Namespace) -> int:
    errors = validate_bundle_file(Path(args.bundle))
    if errors:
        for error in errors:
            print(f"error={error}", file=sys.stderr)
        return 1
    print("bundle_status=valid")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    payload = dry_run_bundle(Path(args.bundle))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") != "invalid" else 1


def cmd_dispatch(args: argparse.Namespace) -> int:
    payload = dispatch_bundle(Path(args.bundle))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") in {"completed", "blocked"} else 1


def cmd_status(args: argparse.Namespace) -> int:
    payload = status_for_run(args.run_id, Path(args.portfolio_os_root))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") != "missing" else 1


def cmd_resume(args: argparse.Namespace) -> int:
    payload = resume_run(args.run_id, Path(args.portfolio_os_root))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") not in {"missing_bundle"} else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "portfolio-os":
        argv = argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
