"""Validation and Paperclip handoff boundary for Portfolio-OS bundles.

This plugin intentionally does not implement Portfolio-OS tasks itself. Real
issue-backed inference must run through Paperclip's external adapter after the
control plane resolves and receipts one provider-policy route. Keeping this
module validation/handoff-only prevents canned documents, guessed QA commands,
or a local git commit from being mistaken for completed agent work.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .contract import (
    HERMES_TASK_BUNDLE_SCHEMA_VERSION,
    internet_pipes_contract,
    is_execution_bundle,
    load_bundle,
    validate_bundle,
)


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)\b(?:sk|rk|pk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(
        r"(?is)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
        r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
]
SECRET_ENV_NAME = re.compile(
    r"(?i)(?:api_?key|access_?key|access_?token|auth_?token|token|secret|password|"
    r"credentials?|authorization|private_?key)$"
)


def validate_bundle_file(bundle_path: Path, *, require_target_exists: bool = True) -> list[str]:
    return validate_bundle(load_bundle(bundle_path), require_target_exists=require_target_exists)


def dry_run_bundle(bundle_path: Path) -> dict[str, Any]:
    bundle = load_bundle(bundle_path)
    errors = validate_bundle(bundle, require_target_exists=True)
    if errors:
        return {"status": "invalid", "errors": [_redact_text(error) for error in errors]}
    tasks = [task for task in bundle.get("tasks", []) if isinstance(task, Mapping)]
    payload = _redact_payload({
        "schema_version": "hermes.portfolio_os_dry_run.v2",
        "generated_at": _now(),
        "run_id": str(bundle["run"]["run_id"]),
        "bundle_schema_version": bundle.get("schema_version"),
        "bundle_source_sha256": _source_sha256(bundle_path),
        "bundle_canonical_sha256": _canonical_sha256(bundle),
        "target_repo": bundle["target"]["repo_full_name"],
        "local_repo_path": str(Path(str(bundle["target"]["local_repo_path"])).expanduser().resolve(strict=False)),
        "working_branch": bundle["target"].get("working_branch"),
        "internet_pipes": internet_pipes_contract(bundle),
        "tasks_planned": [
            {
                "id": task.get("id", ""),
                "type": task.get("type", ""),
                "title": task.get("title", ""),
                "files_expected": task.get("files_expected", []),
            }
            for task in tasks
        ],
        "would_modify": _unique_expected_files(tasks),
        "execution_authority": "paperclip_control_plane",
        "required_adapter_type": "hermes_local",
        "status": "dry_run_complete",
    })
    _write_json(_status_dir(bundle) / f"{bundle['run']['run_id']}.dry_run.json", payload)
    return payload


def dispatch_bundle(bundle_path: Path) -> dict[str, Any]:
    """Validate a bundle and emit a non-success Paperclip handoff receipt.

    No target-repository file, branch, commit, test command, provider, or model
    is touched here. Paperclip must pass the bundle to the external adapter and
    later persist that adapter's true-final, usage, QA, and artifact receipts.
    """
    bundle = load_bundle(bundle_path)
    errors = validate_bundle(bundle, require_target_exists=True)
    if errors:
        raise ValueError("; ".join(_redact_text(error) for error in errors))

    legacy = not is_execution_bundle(bundle)
    disposition = "legacy_validation_only" if legacy else "external_adapter_handoff_required"
    error_code = "legacy_bundle_dispatch_disabled" if legacy else "paperclip_external_adapter_required"
    blocker = (
        "Legacy pos.hermes_task_bundle.v1 bundles are validation-only and cannot dispatch mutations."
        if legacy
        else "Portfolio-OS execution requires the Paperclip hermes_local external adapter; "
        "this plugin cannot generate artifacts, run inference, commit, push, or declare completion."
    )
    governance = bundle.get("governance", {}) if isinstance(bundle.get("governance"), Mapping) else {}
    execution = bundle.get("execution", {}) if isinstance(bundle.get("execution"), Mapping) else {}
    payload = _redact_payload({
        "schema_version": "hermes.portfolio_os_handoff.v2",
        "generated_at": _now(),
        "run_id": str(bundle["run"]["run_id"]),
        "bundle_schema_version": bundle.get("schema_version"),
        "bundle_source_sha256": _source_sha256(bundle_path),
        "bundle_canonical_sha256": _canonical_sha256(bundle),
        "status": "blocked" if legacy else "pending",
        "terminal": False,
        "disposition": disposition,
        "error_code": error_code,
        "blockers": [blocker],
        "next_actions": [
            "Dispatch this immutable bundle through Paperclip's hermes_local external adapter "
            "using governance.resolved_route and persist the adapter's true-final receipt."
        ] if not legacy else ["Regenerate this bundle as a governance-bound pos.hermes_task_bundle.v2 handoff."],
        "execution_authority": "paperclip_control_plane",
        "required_adapter_type": "hermes_local",
        "target_repo": bundle["target"]["repo_full_name"],
        "local_repo_path": str(Path(str(bundle["target"]["local_repo_path"])).expanduser().resolve(strict=False)),
        "branch": bundle["target"].get("working_branch"),
        "commit_sha": "",
        "pushed_to_origin": False,
        "files_changed": [],
        "tasks_completed": [],
        "tasks_failed": [],
        "tests_run": [],
        "qa_status": "not_started",
        "completion_evidence": [],
        "internet_pipes": internet_pipes_contract(bundle),
        "governance": governance,
        "execution": execution,
        "paperclip_execution_id": str(bundle.get("paperclip", {}).get("paperclip_execution_id", "")),
        "paperclip_issue_ids": bundle.get("paperclip", {}).get("issue_ids", []),
    })
    _write_json(Path(str(bundle["outputs"]["result_path"])), payload)
    _write_log(bundle, payload)
    return payload


def status_for_run(
    run_id: str,
    portfolio_os_root: Path = Path("/Users/mnm/Documents/Github/portfolio-os"),
) -> dict[str, Any]:
    result_path = portfolio_os_root / "data/hermes_results" / f"{run_id}.json"
    if result_path.exists():
        return _redact_payload(load_bundle(result_path))
    dry_run_path = portfolio_os_root / "data/hermes_status" / f"{run_id}.dry_run.json"
    if dry_run_path.exists():
        return _redact_payload(load_bundle(dry_run_path))
    return {
        "run_id": run_id,
        "status": "blocked",
        "terminal": False,
        "error_code": "handoff_receipt_missing",
        "blockers": [f"No Hermes handoff artifact found for run_id {run_id}."],
    }


def resume_run(
    run_id: str,
    portfolio_os_root: Path = Path("/Users/mnm/Documents/Github/portfolio-os"),
) -> dict[str, Any]:
    bundle_path = portfolio_os_root / "data/hermes_task_bundles" / f"{run_id}.json"
    if not bundle_path.exists():
        return {
            "run_id": run_id,
            "status": "blocked",
            "terminal": False,
            "error_code": "bundle_missing",
            "blockers": [f"Missing bundle: {bundle_path}"],
        }
    return dispatch_bundle(bundle_path)


def _source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(bundle: Mapping[str, Any]) -> str:
    encoded = json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _configured_secret_values() -> list[str]:
    values = {
        value.strip()
        for key, value in os.environ.items()
        if SECRET_ENV_NAME.search(key) and isinstance(value, str) and len(value.strip()) >= 8
    }
    return sorted(values, key=len, reverse=True)


def _redact_text(value: Any) -> str:
    text = str(value)
    for secret in _configured_secret_values():
        text = text.replace(secret, "[redacted]")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def _redact_payload(value: Any, key: str = "") -> Any:
    normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
    if normalized_key in {
        "apikey", "accesskey", "accesstoken", "authtoken", "authorization",
        "clientsecret", "credential", "credentials", "password", "privatekey", "secret",
    } and value is not None and value != "":
        return "[redacted]"
    if isinstance(value, Mapping):
        return {str(child_key): _redact_payload(child_value, str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_payload(item) for item in value]
    return _redact_text(value) if isinstance(value, str) else value


def _unique_expected_files(tasks: list[Mapping[str, Any]]) -> list[str]:
    files: list[str] = []
    for task in tasks:
        for item in task.get("files_expected", []):
            if isinstance(item, str) and item not in files:
                files.append(item)
    return files


def _write_log(bundle: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    path = Path(str(bundle["outputs"]["execution_log_path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = _redact_payload(result)
    lines = [
        f"run_id={safe['run_id']}",
        f"status={safe['status']}",
        f"disposition={safe['disposition']}",
        f"bundle_source_sha256={safe['bundle_source_sha256']}",
        f"result={json.dumps(safe, sort_keys=True)}",
    ]
    _atomic_write_text(path, "\n".join(lines) + "\n")


def _status_dir(bundle: Mapping[str, Any]) -> Path:
    result_path = Path(str(bundle["outputs"]["result_path"]))
    return result_path.parent.parent / "hermes_status"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    safe = _redact_payload(dict(payload))
    _atomic_write_text(path, json.dumps(safe, indent=2, sort_keys=True) + "\n")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "dispatch_bundle",
    "dry_run_bundle",
    "resume_run",
    "status_for_run",
    "validate_bundle_file",
]
