from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .contract import internet_pipes_contract, load_bundle, validate_bundle


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
]


@dataclass
class ExecutionState:
    run_id: str
    bundle_path: Path
    target_repo: str
    local_repo_path: Path
    branch: str
    commit_sha: str = ""
    pushed_to_origin: bool = False
    files_changed: list[str] = field(default_factory=list)
    tasks_completed: list[str] = field(default_factory=list)
    tasks_failed: list[dict[str, str]] = field(default_factory=list)
    tests_run: list[dict[str, Any]] = field(default_factory=list)
    qa_status: str = "pending"
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    status: str = "pending"


def validate_bundle_file(bundle_path: Path, *, require_target_exists: bool = True) -> list[str]:
    return validate_bundle(load_bundle(bundle_path), require_target_exists=require_target_exists)


def dry_run_bundle(bundle_path: Path) -> dict[str, Any]:
    bundle = load_bundle(bundle_path)
    errors = validate_bundle(bundle, require_target_exists=True)
    if errors:
        return {"status": "invalid", "errors": errors}
    state = _initial_state(bundle, bundle_path)
    planned = [
        {
            "id": task.get("id", ""),
            "type": task.get("type", ""),
            "title": task.get("title", ""),
            "files_expected": task.get("files_expected", []),
        }
        for task in bundle.get("tasks", [])
        if isinstance(task, Mapping)
    ]
    payload = {
        "schema_version": "hermes.portfolio_os_dry_run.v1",
        "generated_at": _now(),
        "run_id": state.run_id,
        "target_repo": state.target_repo,
        "local_repo_path": str(state.local_repo_path),
        "working_branch": state.branch,
        "internet_pipes": internet_pipes_contract(bundle),
        "tasks_planned": planned,
        "would_modify": _unique_expected_files(planned),
        "status": "dry_run_complete",
    }
    _write_json(_status_dir(bundle) / f"{state.run_id}.dry_run.json", payload)
    return payload


def dispatch_bundle(bundle_path: Path) -> dict[str, Any]:
    bundle = load_bundle(bundle_path)
    errors = validate_bundle(bundle, require_target_exists=True)
    if errors:
        raise ValueError("; ".join(errors))
    state = _initial_state(bundle, bundle_path)
    target = state.local_repo_path
    if not (target / ".git").exists():
        state.blockers.append("Target path is not a git repository.")
        state.status = "blocked"
        result = _result_payload(bundle, state)
        _write_json(Path(str(bundle["outputs"]["result_path"])), result)
        return result

    initial_status = _git(target, ["status", "--porcelain"], check=False).stdout
    if initial_status.strip():
        state.blockers.append("Target repository must be clean before dispatch.")
        state.status = "blocked"
        result = _result_payload(bundle, state)
        _write_json(Path(str(bundle["outputs"]["result_path"])), result)
        _write_log(bundle, state, result)
        return result

    _ensure_branch(bundle, state)
    before = _git(target, ["status", "--short"], check=False).stdout
    for task in sorted([task for task in bundle.get("tasks", []) if isinstance(task, Mapping)], key=lambda item: int(item.get("priority", 100))):
        try:
            changed = _execute_task(bundle, state, task)
            state.files_changed.extend(changed)
            state.tasks_completed.append(str(task.get("id", "")))
        except Exception as exc:  # noqa: BLE001
            state.tasks_failed.append({"id": str(task.get("id", "")), "error": str(exc)})
    _run_quality_checks(state)
    after = _git(target, ["status", "--short"], check=False).stdout
    if before != after:
        secret_hits = _scan_for_secrets(target, state.files_changed)
        if secret_hits:
            state.blockers.extend([f"Secret-like content refused: {hit}" for hit in secret_hits])
            state.status = "blocked"
        else:
            _git(target, ["add", "--", *sorted(set(state.files_changed))], check=True)
            if _git(target, ["diff", "--cached", "--quiet"], check=False).returncode == 0:
                state.status = "completed"
            else:
                message = f"chore(portfolio-os): execute {bundle['opportunity']['mandate_type']} for {state.run_id}"
                _git(target, ["commit", "-m", message], check=True)
                state.commit_sha = _git(target, ["rev-parse", "HEAD"], check=True).stdout.strip()
                _maybe_push(bundle, state)
                state.status = "completed"
    else:
        state.status = "completed"
        state.next_actions.append("No target repo changes were necessary for the completed tasks.")
    result = _result_payload(bundle, state)
    _write_json(Path(str(bundle["outputs"]["result_path"])), result)
    _write_log(bundle, state, result)
    return result


def status_for_run(run_id: str, portfolio_os_root: Path = Path("/Users/mnm/Documents/Github/portfolio-os")) -> dict[str, Any]:
    result_path = portfolio_os_root / "data/hermes_results" / f"{run_id}.json"
    if result_path.exists():
        return load_bundle(result_path)
    dry_run_path = portfolio_os_root / "data/hermes_status" / f"{run_id}.dry_run.json"
    if dry_run_path.exists():
        return load_bundle(dry_run_path)
    return {"run_id": run_id, "status": "missing", "blockers": [f"No Hermes artifact found for run_id {run_id}."]}


def resume_run(run_id: str, portfolio_os_root: Path = Path("/Users/mnm/Documents/Github/portfolio-os")) -> dict[str, Any]:
    bundle_path = portfolio_os_root / "data/hermes_task_bundles" / f"{run_id}.json"
    if not bundle_path.exists():
        return {"run_id": run_id, "status": "missing_bundle", "blockers": [f"Missing bundle: {bundle_path}"]}
    return dispatch_bundle(bundle_path)


def _initial_state(bundle: Mapping[str, Any], bundle_path: Path) -> ExecutionState:
    run = bundle["run"]
    target = bundle["target"]
    return ExecutionState(
        run_id=str(run["run_id"]),
        bundle_path=bundle_path,
        target_repo=str(target["repo_full_name"]),
        local_repo_path=Path(str(target["local_repo_path"])).expanduser().resolve(strict=False),
        branch=str(target.get("working_branch") or f"run/{run['run_id']}/portfolio-os-flywheel"),
    )


def _ensure_branch(bundle: Mapping[str, Any], state: ExecutionState) -> None:
    target = state.local_repo_path
    write_policy = bundle["target"].get("write_policy", {})
    if write_policy.get("local_only"):
        return
    current = _git(target, ["branch", "--show-current"], check=False).stdout.strip()
    if current == state.branch:
        return
    if _git(target, ["rev-parse", "--verify", state.branch], check=False).returncode == 0:
        _git(target, ["switch", state.branch], check=True)
    else:
        _git(target, ["switch", "-c", state.branch], check=True)


def _execute_task(bundle: Mapping[str, Any], state: ExecutionState, task: Mapping[str, Any]) -> list[str]:
    task_type = str(task.get("type", "docs"))
    if task_type == "QA":
        _run_quality_checks(state)
        return []
    if task_type == "code_change":
        return _write_docs_asset(state.local_repo_path, "docs/issue_plan.md", task, fallback_title="Implementation Plan")
    if task_type == "README":
        return _append_readme(state.local_repo_path, bundle, task)
    file_map = {
        "docs": "docs/execution_notes.md",
        "landing_page": "docs/landing_page_copy.md",
        "homepage": "docs/homepage_plan.md",
        "lead_magnet": "docs/lead_magnet.md",
        "pricing": "docs/pricing.md",
        "GTM": "docs/gtm_strategy.md",
        "trust_packet": "docs/trust_packet.md",
        "issue_plan": "docs/issue_plan.md",
        "business_plan": "docs/business_plan.md",
        "validation_plan": "docs/validation_plan.md",
        "analytics": "docs/analytics_plan.md",
        "deployment": "docs/deployment_checklist.md",
    }
    return _write_docs_asset(state.local_repo_path, file_map.get(task_type, "docs/execution_notes.md"), task)


def _write_docs_asset(root: Path, relative_path: str, task: Mapping[str, Any], *, fallback_title: str | None = None) -> list[str]:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    title = fallback_title or str(task.get("title") or "Portfolio-OS Execution Asset")
    body = [
        f"# {title}",
        "",
        str(task.get("instructions") or "Generated by Hermes-Agent from a Portfolio-OS task bundle."),
        "",
        "## Acceptance Criteria",
        "",
    ]
    criteria = task.get("acceptance_criteria") if isinstance(task.get("acceptance_criteria"), list) else []
    body.extend([f"- {item}" for item in criteria] or ["- Review and complete this artifact."])
    body.append("")
    path.write_text("\n".join(body), encoding="utf-8")
    return [relative_path]


def _append_readme(root: Path, bundle: Mapping[str, Any], task: Mapping[str, Any]) -> list[str]:
    path = root / "README.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = "<!-- PORTFOLIO_OS_BUSINESS_VALUE_START -->"
    if marker in existing:
        return []
    opportunity = bundle.get("opportunity", {})
    internet_pipes = internet_pipes_contract(bundle)
    missing = ", ".join(internet_pipes["missing_stations"]) if internet_pipes["missing_stations"] else "none"
    addition = (
        "\n\n"
        "<!-- PORTFOLIO_OS_BUSINESS_VALUE_START -->\n"
        "## Portfolio-OS Business Value Hypothesis\n\n"
        f"- Niche: {opportunity.get('niche') or 'validation target'}\n"
        f"- Strongest wedge: {opportunity.get('strongest_wedge') or 'pending validation'}\n"
        f"- Evidence gate: {opportunity.get('evidence_gate_status') or 'unknown'}\n"
        f"- Internet Pipes: score={internet_pipes['score']:.2f}, readiness={internet_pipes['readiness'] or 'unknown'}, missing_stations={missing}\n"
        "- This section is appended by Hermes-Agent from a Portfolio-OS validation bundle and should be treated as a hypothesis until evidence gates clear.\n"
        "<!-- PORTFOLIO_OS_BUSINESS_VALUE_END -->\n"
    )
    path.write_text(existing.rstrip() + addition, encoding="utf-8")
    return ["README.md"]


def _run_quality_checks(state: ExecutionState) -> None:
    root = state.local_repo_path
    candidates = [
        (["pytest"], root / "pytest.ini"),
        (["npm", "test", "--", "--runInBand"], root / "package.json"),
        (["pnpm", "test"], root / "pnpm-lock.yaml"),
    ]
    for command, marker in candidates:
        if not marker.exists():
            continue
        proc = _run(command, cwd=root)
        state.tests_run.append({"command": " ".join(command), "returncode": proc.returncode})
        state.qa_status = "passed" if proc.returncode == 0 else "failed"
        if proc.returncode != 0:
            state.blockers.append(f"Quality command failed: {' '.join(command)}")
        return
    state.qa_status = "not_run"


def _maybe_push(bundle: Mapping[str, Any], state: ExecutionState) -> None:
    push_policy = bundle["target"].get("push_policy", {})
    if push_policy.get("no_push") or not push_policy.get("push_to_origin"):
        state.pushed_to_origin = False
        return
    proc = _git(state.local_repo_path, ["push", "-u", "origin", state.branch], check=False)
    state.pushed_to_origin = proc.returncode == 0
    if proc.returncode != 0:
        state.blockers.append((proc.stderr or proc.stdout or "git push failed").strip())


def _scan_for_secrets(root: Path, relative_paths: list[str]) -> list[str]:
    hits: list[str] = []
    for relative in sorted(set(relative_paths)):
        path = root / relative
        if not path.is_file() or path.stat().st_size > 512_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            hits.append(relative)
    return hits


def _unique_expected_files(planned: list[Mapping[str, Any]]) -> list[str]:
    files: list[str] = []
    for task in planned:
        for item in task.get("files_expected", []):
            if isinstance(item, str) and item not in files:
                files.append(item)
    return files


def _result_payload(bundle: Mapping[str, Any], state: ExecutionState) -> dict[str, Any]:
    paperclip = bundle.get("paperclip", {})
    return {
        "run_id": state.run_id,
        "status": state.status,
        "target_repo": state.target_repo,
        "local_repo_path": str(state.local_repo_path),
        "branch": state.branch,
        "commit_sha": state.commit_sha,
        "pushed_to_origin": state.pushed_to_origin,
        "internet_pipes": internet_pipes_contract(bundle),
        "files_changed": sorted(set(state.files_changed)),
        "tasks_completed": [item for item in state.tasks_completed if item],
        "tasks_failed": state.tasks_failed,
        "tests_run": state.tests_run,
        "qa_status": state.qa_status,
        "blockers": state.blockers,
        "next_actions": state.next_actions,
        "paperclip_execution_id": str(paperclip.get("paperclip_execution_id", "")),
        "paperclip_issue_ids": paperclip.get("issue_ids", []),
        "gstack_artifacts": bundle.get("gstack", {}),
    }


def _write_log(bundle: Mapping[str, Any], state: ExecutionState, result: Mapping[str, Any]) -> None:
    path = Path(str(bundle["outputs"]["execution_log_path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"run_id={state.run_id}",
        f"status={state.status}",
        f"target_repo={state.target_repo}",
        f"branch={state.branch}",
        f"internet_pipes={json.dumps(internet_pipes_contract(bundle), sort_keys=True)}",
        f"commit_sha={state.commit_sha or 'n/a'}",
        f"result={json.dumps(result, sort_keys=True)}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _status_dir(bundle: Mapping[str, Any]) -> Path:
    result_path = Path(str(bundle["outputs"]["result_path"]))
    return result_path.parent.parent / "hermes_status"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(cwd: Path, args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
        stdin=subprocess.DEVNULL,
    )


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 124, "", str(exc))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
