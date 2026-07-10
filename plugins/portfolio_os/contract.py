from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


HERMES_TASK_BUNDLE_SCHEMA_VERSION = "pos.hermes_task_bundle.v1"
MANDATE_TYPES = {"launch_execution", "validation_sprint", "research_backfill", "internal_leverage"}
INTERNET_PIPES_STATIONS = {
    "generation",
    "validation",
    "evaluation",
    "differentiation",
    "visualization",
    "recommendation",
}
INTERNET_PIPES_LAUNCH_READY = {"alpha_ready", "factory_ready"}
TASK_TYPES = {
    "code_change",
    "docs",
    "landing_page",
    "homepage",
    "lead_magnet",
    "pricing",
    "GTM",
    "README",
    "trust_packet",
    "QA",
    "deployment",
    "analytics",
    "issue_plan",
    "business_plan",
    "validation_plan",
}
FORBIDDEN_OPERATIONS = {"delete_repo", "rewrite_history", "remove_license", "commit_secrets"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split("|") if item.strip()]


def _float_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _canonical_internet_pipes(raw: Mapping[str, Any]) -> dict[str, Any]:
    score = _float_value(raw.get("score"))
    return {
        "score": round(score if score is not None else 0.0, 2),
        "readiness": str(raw.get("readiness", "") or "").strip(),
        "missing_stations": _string_list(raw.get("missing_stations")),
        "recommendations": _string_list(raw.get("recommendations")),
    }


def internet_pipes_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the normalized Internet Pipes block carried by a POS task bundle."""
    opportunity = _mapping(payload.get("opportunity"))
    evidence = _mapping(payload.get("evidence"))
    opportunity_contract = _mapping(opportunity.get("internet_pipes"))
    evidence_contract = _mapping(evidence.get("internet_pipes"))
    raw = opportunity_contract or evidence_contract
    return _canonical_internet_pipes(raw)


def load_bundle(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("bundle must be a JSON object")
    return payload


def validate_bundle(payload: Mapping[str, Any], *, require_target_exists: bool = True) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != HERMES_TASK_BUNDLE_SCHEMA_VERSION:
        errors.append(f"schema_version must equal {HERMES_TASK_BUNDLE_SCHEMA_VERSION}")
    run = _mapping(payload.get("run"))
    run_id = str(run.get("run_id", "")).strip()
    if not run_id:
        errors.append("run.run_id is required")
    target = _mapping(payload.get("target"))
    target_path_raw = str(target.get("local_repo_path", "")).strip()
    if not str(target.get("repo_full_name", "")).strip():
        errors.append("target.repo_full_name is required")
    if not target_path_raw:
        errors.append("target.local_repo_path is required")
    else:
        target_path = Path(target_path_raw).expanduser()
        if require_target_exists and not target_path.exists():
            errors.append(f"target.local_repo_path does not exist: {target_path}")
        allowed = _allowed_roots()
        resolved = target_path.resolve(strict=False)
        if not any(_inside(resolved, root) for root in allowed):
            errors.append("target.local_repo_path is outside allowed roots")

    write_policy = _mapping(target.get("write_policy"))
    push_policy = _mapping(target.get("push_policy"))
    if bool(write_policy.get("local_only")) and (
        bool(push_policy.get("push_to_origin")) or bool(push_policy.get("create_pr"))
    ):
        errors.append("write_policy.local_only conflicts with push/create_pr")
    if bool(push_policy.get("no_push")) and (
        bool(push_policy.get("push_to_origin")) or bool(push_policy.get("create_pr"))
    ):
        errors.append("push_policy.no_push conflicts with push/create_pr")

    opportunity = _mapping(payload.get("opportunity"))
    mandate_type = str(opportunity.get("mandate_type", "")).strip()
    if mandate_type not in MANDATE_TYPES:
        errors.append(f"opportunity.mandate_type must be one of {sorted(MANDATE_TYPES)}")
    _validate_internet_pipes_contract(payload, mandate_type, errors)

    tasks = _list(payload.get("tasks"))
    if not tasks:
        errors.append("tasks must not be empty")
    seen: set[str] = set()
    for index, raw_task in enumerate(tasks):
        task = _mapping(raw_task)
        task_id = str(task.get("id", "")).strip()
        task_type = str(task.get("type", "")).strip()
        if not task_id:
            errors.append(f"tasks[{index}].id is required")
        elif task_id in seen:
            errors.append(f"duplicate task id: {task_id}")
        seen.add(task_id)
        if task_type not in TASK_TYPES:
            errors.append(f"tasks[{index}].type must be one of {sorted(TASK_TYPES)}")
        task_text = json.dumps(task, sort_keys=True).lower()
        for forbidden in FORBIDDEN_OPERATIONS:
            if forbidden in task_text:
                errors.append(f"tasks[{index}] references forbidden operation {forbidden}")

    safety = _mapping(payload.get("safety"))
    if safety.get("destructive_ops_allowed") is not False:
        errors.append("safety.destructive_ops_allowed must be false")
    if safety.get("secrets_scan_required") is not True:
        errors.append("safety.secrets_scan_required must be true")
    missing = FORBIDDEN_OPERATIONS - {str(item) for item in _list(safety.get("forbidden_operations"))}
    if missing:
        errors.append(f"safety.forbidden_operations missing {sorted(missing)}")
    return errors


def _validate_internet_pipes_contract(payload: Mapping[str, Any], mandate_type: str, errors: list[str]) -> None:
    opportunity = _mapping(payload.get("opportunity"))
    evidence = _mapping(payload.get("evidence"))
    opportunity_contract = _mapping(opportunity.get("internet_pipes"))
    evidence_contract = _mapping(evidence.get("internet_pipes"))
    if not opportunity_contract:
        errors.append("opportunity.internet_pipes is required")
        return
    if not evidence_contract:
        errors.append("evidence.internet_pipes is required")

    if "score" not in opportunity_contract:
        errors.append("opportunity.internet_pipes.score is required")
    elif _float_value(opportunity_contract.get("score")) is None:
        errors.append("opportunity.internet_pipes.score must be numeric")
    readiness = str(opportunity_contract.get("readiness", "") or "").strip()
    if not readiness:
        errors.append("opportunity.internet_pipes.readiness is required")
    missing_stations = _string_list(opportunity_contract.get("missing_stations"))
    unknown = sorted(set(missing_stations) - INTERNET_PIPES_STATIONS)
    if unknown:
        errors.append(f"opportunity.internet_pipes.missing_stations contains unknown stations: {unknown}")
    recommendations = opportunity_contract.get("recommendations")
    if recommendations is not None and not isinstance(recommendations, list):
        errors.append("opportunity.internet_pipes.recommendations must be a list when present")

    if evidence_contract and _canonical_internet_pipes(evidence_contract) != _canonical_internet_pipes(opportunity_contract):
        errors.append("evidence.internet_pipes must match opportunity.internet_pipes")

    if mandate_type == "launch_execution":
        if readiness not in INTERNET_PIPES_LAUNCH_READY:
            errors.append("launch_execution requires Internet Pipes readiness alpha_ready or factory_ready")
        if missing_stations:
            errors.append("launch_execution requires no missing Internet Pipes stations")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _allowed_roots() -> list[Path]:
    roots = [
        Path("/Users/mnm/Documents/Github"),
        Path("/tmp"),
        Path("/private/tmp"),
    ]
    extra = os.environ.get("HERMES_PORTFOLIO_OS_ALLOWED_ROOTS", "")
    for raw in extra.split(os.pathsep):
        raw = raw.strip()
        if raw:
            roots.append(Path(raw).expanduser())
    return [root.resolve(strict=False) for root in roots]
