from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_state import SessionDB
from plugins.portfolio_os import contract as portfolio_contract
from plugins.portfolio_os.contract import (
    PROFIT_FLYWHEEL_CONTRACT_ID,
    PROFIT_FLYWHEEL_SCHEMA_VERSION,
    validate_bundle,
)
from plugins.portfolio_os.runtime import (
    dispatch_bundle,
    dry_run_bundle,
    status_for_run,
    validate_bundle_file,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
@pytest.fixture(autouse=True)
def allow_test_target_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib

    monkeypatch.setenv("HERMES_PORTFOLIO_OS_ALLOWED_ROOTS", str(tmp_path))
    contract_dir = tmp_path / "contracts"
    contract_dir.mkdir()
    contract_path = contract_dir / "profit-flywheel.v2.json"
    contract_schema_path = contract_dir / "profit-flywheel.v2.schema.json"
    run_schema_path = contract_dir / "profit-flywheel.run.v2.schema.json"
    dispatch_schema_path = contract_dir / "pos.dispatch.v2.schema.json"
    learning_schema_path = contract_dir / "pos.learning_receipt.v2.schema.json"
    schema_fixture = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}
    for schema_path in (contract_schema_path, run_schema_path, dispatch_schema_path, learning_schema_path):
        schema_path.write_text(json.dumps(schema_fixture), encoding="utf-8")
    run_schema_sha256 = hashlib.sha256(run_schema_path.read_bytes()).hexdigest()
    dispatch_schema_sha256 = hashlib.sha256(dispatch_schema_path.read_bytes()).hexdigest()
    learning_schema_sha256 = hashlib.sha256(learning_schema_path.read_bytes()).hexdigest()
    contract_path.write_text(
        json.dumps({
            "contract_id": PROFIT_FLYWHEEL_CONTRACT_ID,
            "schema_version": PROFIT_FLYWHEEL_SCHEMA_VERSION,
            "artifact_schemas": {
                "run_receipt": {
                    "schema_version": "profit-flywheel.run.v2",
                    "path": "contracts/profit-flywheel.run.v2.schema.json",
                    "sha256": run_schema_sha256,
                },
                "dispatch": {
                    "schema_version": "pos.dispatch.v2",
                    "path": "contracts/pos.dispatch.v2.schema.json",
                    "sha256": dispatch_schema_sha256,
                },
            },
        }),
        encoding="utf-8",
    )
    contract_sha256 = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    contract_schema_sha256 = hashlib.sha256(contract_schema_path.read_bytes()).hexdigest()
    monkeypatch.setattr(portfolio_contract, "PINNED_PROFIT_FLYWHEEL_CONTRACT_SHA256", contract_sha256)
    monkeypatch.setattr(
        portfolio_contract,
        "PINNED_PROFIT_FLYWHEEL_CONTRACT_SCHEMA_SHA256",
        contract_schema_sha256,
    )
    monkeypatch.setattr(portfolio_contract, "PINNED_PROFIT_FLYWHEEL_RUN_SCHEMA_SHA256", run_schema_sha256)
    monkeypatch.setattr(portfolio_contract, "PINNED_POS_DISPATCH_SCHEMA_SHA256", dispatch_schema_sha256)
    monkeypatch.setattr(
        portfolio_contract,
        "PINNED_POS_LEARNING_RECEIPT_SCHEMA_SHA256",
        learning_schema_sha256,
    )
    policy_path = contract_dir / "provider-policy.v2.json"
    policy_schema_path = contract_dir / "provider-policy.v2.schema.json"
    policy_path.write_text(
        json.dumps({
            "schemaVersion": "provider-policy.v2",
            "routes": {
                "route-fixture": {
                    "provider": "fixture-provider",
                    "model": {"kind": "exact", "value": "fixture-model", "version": "fixture-v1"},
                }
            },
        }),
        encoding="utf-8",
    )
    policy_schema_path.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    monkeypatch.setenv("PAPERCLIP_PROFIT_FLYWHEEL_CONTRACT_PATH", str(contract_path))
    monkeypatch.setenv("PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_PATH", str(contract_schema_path))
    monkeypatch.setenv("PAPERCLIP_PROFIT_FLYWHEEL_SHA256", contract_sha256)
    monkeypatch.setenv(
        "PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_SHA256",
        contract_schema_sha256,
    )
    monkeypatch.setenv("PAPERCLIP_PROVIDER_POLICY_PATH", str(policy_path))
    monkeypatch.setenv("PAPERCLIP_PROVIDER_POLICY_SCHEMA_PATH", str(policy_schema_path))
    monkeypatch.setenv("PAPERCLIP_PROVIDER_POLICY_SHA256", hashlib.sha256(policy_path.read_bytes()).hexdigest())
    monkeypatch.setenv(
        "PAPERCLIP_PROVIDER_POLICY_SCHEMA_SHA256",
        hashlib.sha256(policy_schema_path.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("PAPERCLIP_RESOLVED_ROUTE_ID", "route-fixture")
    monkeypatch.setenv("PAPERCLIP_RESOLVED_PROVIDER", "fixture-provider")
    monkeypatch.setenv("PAPERCLIP_RESOLVED_MODEL", "fixture-model")
    monkeypatch.setenv("PAPERCLIP_RESOLVED_MODEL_VERSION", "fixture-v1")
    monkeypatch.setenv("HERMES_PORTFOLIO_OS_OUTPUT_ROOTS", str(tmp_path / "portfolio-os/data"))


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def _init_target_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "target"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "README.md").write_text("# Fixture Target\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init")
    return repo


def _bundle(tmp_path: Path, target_repo: Path) -> dict:
    pos_root = tmp_path / "portfolio-os"
    run_id = "fixture-validation-sprint"
    internet_pipes = {
        "score": 63.5,
        "readiness": "promising",
        "missing_stations": ["differentiation"],
        "recommendations": ["Add explicit differentiation evidence from review gaps."],
    }
    return {
        "schema_version": "pos.hermes_task_bundle.v2",
        "run": {
            "run_id": run_id,
            "generated_at": "2026-06-01T00:00:00+00:00",
            "portfolio_os_commit": "fixture",
            "paperclip_execution_id": "pc-fixture",
            "snapshot_hash": "fixture",
            "mandate_hash": "fixture",
            "execution_mandate_hash": "fixture",
        },
        "governance": {
            "execution_authority": "paperclip_control_plane",
            "profit_flywheel_contract": {
                "id": PROFIT_FLYWHEEL_CONTRACT_ID,
                "schema_version": PROFIT_FLYWHEEL_SCHEMA_VERSION,
                "path": os.environ["PAPERCLIP_PROFIT_FLYWHEEL_CONTRACT_PATH"],
                "schema_path": os.environ["PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_PATH"],
                "sha256": os.environ["PAPERCLIP_PROFIT_FLYWHEEL_SHA256"],
                "schema_sha256": os.environ["PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_SHA256"],
            },
            "provider_policy": {
                "policy_id": "provider-policy-fixture",
                "revision": "fixture-r1",
                "schema_version": "provider-policy.v2",
                "path": os.environ["PAPERCLIP_PROVIDER_POLICY_PATH"],
                "schema_path": os.environ["PAPERCLIP_PROVIDER_POLICY_SCHEMA_PATH"],
                "sha256": os.environ["PAPERCLIP_PROVIDER_POLICY_SHA256"],
                "schema_sha256": os.environ["PAPERCLIP_PROVIDER_POLICY_SCHEMA_SHA256"],
            },
            "resolved_route": {
                "route_id": "route-fixture",
                "provider": "fixture-provider",
                "model": "fixture-model",
                "model_version": "fixture-v1",
            },
        },
        "execution": {
            "correlation_id": "correlation-fixture",
            "issue_id": "issue-fixture",
            "stage_id": "validation",
            "budgets": {
                "max_tasks": 8,
                "turns": 20,
                "context_chars": 32000,
                "output_chars": 12000,
                "token_limit": 24000,
                "tool_output_bytes": 16000,
                "tool_output_lines": 320,
                "tool_output_line_chars": 1000,
                "max_escalations": 0,
            },
        },
        "target": {
            "repo_full_name": "owner/target",
            "local_repo_path": str(target_repo),
            "default_branch": "main",
            "working_branch": "run/fixture-validation-sprint/portfolio-os-flywheel",
            "write_policy": {
                "direct_main_allowed": False,
                "branch_then_pr": True,
                "local_only": False,
            },
            "push_policy": {
                "push_to_origin": False,
                "create_pr": False,
                "no_push": True,
            },
        },
        "opportunity": {
            "mandate_type": "validation_sprint",
            "niche": "marketing teams in marketing",
            "persona": "marketing teams",
            "industry": "marketing",
            "region": "us",
            "strongest_wedge": "analytics dashboards for marketing teams",
            "paired_repos": [],
            "evidence_gate_status": "blocked",
            "internet_pipes": internet_pipes,
        },
        "paperclip": {
            "company_id": "company-fixture",
            "company_name": "Portfolio Ventures Lab",
            "project_id": "project-fixture",
            "project_name": "target commercialization sprint",
            "workstream_id": "workstream-fixture",
            "workstream_ids": ["workstream-fixture"],
            "issue_ids": ["issue-fixture"],
            "approval_ids": [],
            "role_assignments": {},
        },
        "team": {
            "company_name": "Portfolio Ventures Lab",
            "project_name": "target commercialization sprint",
            "workstream_id": "workstream-fixture",
            "assigned_role": "Hermes Execution Adapter",
            "assigned_agent": "hermes-agent",
            "paperclip_issue_id": "issue-fixture",
            "paperclip_approval_id": "",
        },
        "tasks": [
            {
                "id": "business-plan",
                "title": "Write business plan",
                "type": "business_plan",
                "instructions": "Create the commercialization business plan.",
                "files_expected": ["docs/business_plan.md"],
                "acceptance_criteria": ["Business plan exists."],
                "dependencies": [],
                "priority": 10,
                "assigned_role": "CEO / Operator",
                "assigned_agent": "hermes-agent",
            },
            {
                "id": "readme-value",
                "title": "Append README value section",
                "type": "README",
                "instructions": "Append business value without truncating existing README.",
                "files_expected": ["README.md"],
                "acceptance_criteria": ["Existing README content is preserved."],
                "dependencies": [],
                "priority": 20,
                "assigned_role": "Engineering Lead",
                "assigned_agent": "hermes-agent",
            },
        ],
        "evidence": {
            "market_signal_ids": [],
            "voc_ids": [],
            "proof_links": [],
            "missing_evidence": ["Need 3 buyer quotes."],
            "confidence": 0.4,
            "gate_status": "blocked",
            "internet_pipes": dict(internet_pipes),
        },
        "gstack": {
            "evidence_backfill_path": str(pos_root / "data/gstack_results/fixture-validation-sprint.evidence_backfill.json"),
            "qa_verification_path": str(pos_root / "data/gstack_results/fixture-validation-sprint.qa_verification.json"),
            "patch_plan_path": str(pos_root / "data/gstack_results/fixture-validation-sprint.patch_plan.json"),
        },
        "safety": {
            "forbidden_operations": ["delete_repo", "rewrite_history", "remove_license", "commit_secrets"],
            "secrets_scan_required": True,
            "destructive_ops_allowed": False,
        },
        "outputs": {
            "result_path": str(pos_root / "data/hermes_results/fixture-validation-sprint.json"),
            "patch_plan_path": str(pos_root / "data/hermes_patch_plans/fixture-validation-sprint.json"),
            "execution_log_path": str(pos_root / "data/hermes_logs/fixture-validation-sprint.log"),
            "files_changed": [],
            "commit_sha": "",
            "pushed_to_origin": False,
            "qa_status": "pending",
            "blockers": [],
            "next_actions": [],
        },
    }


def _write_bundle(tmp_path: Path, target_repo: Path) -> Path:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(_bundle(tmp_path, target_repo), indent=2) + "\n", encoding="utf-8")
    return path


def _enabled_plugin_env(tmp_path: Path) -> dict[str, str]:
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text(
        "plugins:\n  enabled:\n    - portfolio-os\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def _bind_published_profit_flywheel_for_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Subprocesses reload compiled pins, so bind their real frozen files."""
    import hashlib

    contract_path = portfolio_contract.DEFAULT_PROFIT_FLYWHEEL_CONTRACT_PATH
    schema_path = portfolio_contract.DEFAULT_PROFIT_FLYWHEEL_SCHEMA_PATH
    monkeypatch.setenv("PAPERCLIP_PROFIT_FLYWHEEL_CONTRACT_PATH", str(contract_path))
    monkeypatch.setenv("PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_PATH", str(schema_path))
    monkeypatch.setenv(
        "PAPERCLIP_PROFIT_FLYWHEEL_SHA256",
        hashlib.sha256(contract_path.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv(
        "PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_SHA256",
        hashlib.sha256(schema_path.read_bytes()).hexdigest(),
    )


def test_validate_bundle_accepts_valid_bundle(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)

    assert validate_bundle_file(path) == []


def test_plugin_cli_command_accepts_portfolio_os_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_published_profit_flywheel_for_subprocess(monkeypatch)
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes_cli.main",
            "portfolio-os",
            "validate-bundle",
            "--bundle",
            str(path),
        ],
        cwd=REPO_ROOT,
        env=_enabled_plugin_env(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert "bundle_status=valid" in proc.stdout


def test_plugin_cli_command_is_not_loaded_in_safe_mode(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes_cli.main",
            "--safe-mode",
            "portfolio-os",
            "validate-bundle",
            "--bundle",
            str(path),
        ],
        cwd=REPO_ROOT,
        env=_enabled_plugin_env(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode != 0
    assert "portfolio-os" in proc.stderr


def test_destructive_operation_is_refused(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["tasks"][0]["instructions"] = "delete_repo now"

    errors = validate_bundle(bundle)

    assert any("delete_repo" in error for error in errors)


def test_bundle_validation_requires_target_path(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["target"]["local_repo_path"] = ""

    errors = validate_bundle(bundle)

    assert "target.local_repo_path is required" in errors


def test_launch_execution_requires_complete_internet_pipes_readiness(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["opportunity"]["mandate_type"] = "launch_execution"

    errors = validate_bundle(bundle)

    assert "launch_execution requires Internet Pipes readiness alpha_ready or factory_ready" in errors
    assert "launch_execution requires no missing Internet Pipes stations" in errors

    bundle["opportunity"]["internet_pipes"]["readiness"] = "alpha_ready"
    bundle["opportunity"]["internet_pipes"]["missing_stations"] = []
    bundle["evidence"]["internet_pipes"] = dict(bundle["opportunity"]["internet_pipes"])

    assert validate_bundle(bundle) == []


def test_bundle_validation_requires_matching_internet_pipes_evidence_block(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["evidence"]["internet_pipes"]["missing_stations"] = []

    errors = validate_bundle(bundle)

    assert "evidence.internet_pipes must match opportunity.internet_pipes" in errors


def test_dry_run_does_not_mutate_target_repo(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)
    before = _git(repo, "rev-parse", "HEAD")

    payload = dry_run_bundle(path)
    after = _git(repo, "rev-parse", "HEAD")

    assert payload["status"] == "dry_run_complete"
    assert payload["internet_pipes"]["readiness"] == "promising"
    assert payload["internet_pipes"]["missing_stations"] == ["differentiation"]
    assert before == after
    assert not (repo / "docs/business_plan.md").exists()


def test_dispatch_emits_external_adapter_handoff_without_canned_artifacts(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)
    before = _git(repo, "rev-parse", "HEAD")

    result = dispatch_bundle(path)

    assert result["status"] == "pending"
    assert result["terminal"] is False
    assert result["disposition"] == "external_adapter_handoff_required"
    assert result["error_code"] == "paperclip_external_adapter_required"
    assert result["required_adapter_type"] == "hermes_local"
    assert result["internet_pipes"]["readiness"] == "promising"
    assert result["commit_sha"] == ""
    assert result["pushed_to_origin"] is False
    assert result["files_changed"] == []
    assert result["tasks_completed"] == []
    assert result["qa_status"] == "not_started"
    assert result["bundle_source_sha256"] == __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "status", "--porcelain") == ""
    assert not (repo / "docs/business_plan.md").exists()
    result_path = tmp_path / "portfolio-os/data/hermes_results/fixture-validation-sprint.json"
    assert result_path.exists()
    assert json.loads(result_path.read_text(encoding="utf-8"))["disposition"] == result["disposition"]
    log_path = tmp_path / "portfolio-os/data/hermes_logs/fixture-validation-sprint.log"
    assert "disposition=external_adapter_handoff_required" in log_path.read_text(encoding="utf-8")


def test_dispatch_never_touches_dirty_target_repository(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    (repo / "unrelated.txt").write_text("uncommitted\n", encoding="utf-8")
    path = _write_bundle(tmp_path, repo)
    before = _git(repo, "rev-parse", "HEAD")
    before_status = _git(repo, "status", "--porcelain")
    result = dispatch_bundle(path)

    assert result["status"] == "pending"
    assert result["disposition"] == "external_adapter_handoff_required"
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "status", "--porcelain") == before_status
    assert not (repo / "docs/business_plan.md").exists()


def test_handoff_receipt_does_not_persist_secret_bearing_task_text(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    secret = "abcdefghijklmnopqrstuvwx"
    bundle = _bundle(tmp_path, repo)
    bundle["tasks"] = [
        {
            "id": "secret-doc",
            "title": "Credential notes",
            "type": "docs",
            "instructions": f'api_key = "{secret}"',
            "files_expected": ["docs/execution_notes.md"],
            "acceptance_criteria": ["Document exists."],
            "dependencies": [],
            "priority": 10,
            "assigned_role": "Engineering Lead",
            "assigned_agent": "hermes-agent",
        }
    ]
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    result = dispatch_bundle(path)

    persisted = "\n".join(
        item.read_text(encoding="utf-8")
        for item in (tmp_path / "portfolio-os/data").rglob("*")
        if item.is_file()
    )
    assert result["status"] == "pending"
    assert secret not in json.dumps(result)
    assert secret not in persisted
    assert not (repo / "docs/execution_notes.md").exists()


def test_v2_bundle_requires_canonical_contract_and_expected_policy_hashes(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["governance"]["profit_flywheel_contract"]["sha256"] = "0" * 64
    bundle["governance"]["provider_policy"]["sha256"] = "3" * 64

    errors = validate_bundle(bundle)

    assert "governance.profit_flywheel_contract.sha256 does not match the expected SHA-256" in errors
    assert "governance.provider_policy.sha256 does not match the expected SHA-256" in errors


def test_v2_bundle_cannot_redefine_the_frozen_profit_flywheel_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    attacker_selected_pin = "0" * 64
    monkeypatch.setenv("PAPERCLIP_PROFIT_FLYWHEEL_SHA256", attacker_selected_pin)
    bundle["governance"]["profit_flywheel_contract"]["sha256"] = attacker_selected_pin

    errors = validate_bundle(bundle)

    assert "PAPERCLIP_PROFIT_FLYWHEEL_SHA256 does not match the frozen Hermes trust root" in errors
    assert "governance.profit_flywheel_contract.sha256 does not match the expected SHA-256" in errors


@pytest.mark.parametrize(
    ("filename", "expected_error"),
    [
        (
            "profit-flywheel.run.v2.schema.json",
            "frozen profit-flywheel run_receipt schema SHA-256 does not match schema bytes",
        ),
        (
            "pos.dispatch.v2.schema.json",
            "frozen profit-flywheel dispatch schema SHA-256 does not match schema bytes",
        ),
        (
            "pos.learning_receipt.v2.schema.json",
            "frozen POS learning receipt schema SHA-256 does not match schema bytes",
        ),
    ],
)
def test_v2_bundle_rejects_tampered_frozen_artifact_schema_bytes(
    tmp_path: Path,
    filename: str,
    expected_error: str,
) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    contract_path = Path(os.environ["PAPERCLIP_PROFIT_FLYWHEEL_CONTRACT_PATH"])
    (contract_path.parent / filename).write_text('{"type":"string"}', encoding="utf-8")

    errors = validate_bundle(bundle)

    assert expected_error in errors


def test_v2_bundle_requires_exact_resolved_route_and_full_budgets(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["governance"]["resolved_route"]["provider"] = "wrong-provider"
    del bundle["execution"]["budgets"]["context_chars"]
    bundle["execution"]["budgets"]["max_escalations"] = 1

    errors = validate_bundle(bundle)

    assert "governance.resolved_route.provider does not match PAPERCLIP_RESOLVED_PROVIDER" in errors
    assert "governance.resolved_route.provider does not match the pinned route" in errors
    assert "execution.budgets.context_chars must be a positive integer" in errors
    assert "execution.budgets.max_escalations must be 0; route escalation belongs to the control plane" in errors


def test_bundle_output_and_journal_paths_must_stay_under_approved_root(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["outputs"]["result_path"] = str(tmp_path / "outside/result.json")
    bundle["outputs"]["execution_log_path"] = str(tmp_path / "outside/run.log")

    errors = validate_bundle(bundle)

    assert "outputs.result_path is outside HERMES_PORTFOLIO_OS_OUTPUT_ROOTS" in errors
    assert "outputs.execution_log_path is outside HERMES_PORTFOLIO_OS_OUTPUT_ROOTS" in errors
    assert "derived execution journal path is outside HERMES_PORTFOLIO_OS_OUTPUT_ROOTS" in errors


def test_implementation_stage_cannot_authorize_push_or_release(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["target"]["push_policy"] = {
        "push_to_origin": True,
        "create_pr": False,
        "no_push": False,
    }

    errors = validate_bundle(bundle)

    assert "non-release execution stages must set push_policy.no_push and disable push/create_pr" in errors


def test_legacy_v1_bundle_is_validation_only_and_never_mutates(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["schema_version"] = "pos.hermes_task_bundle.v1"
    path = tmp_path / "legacy-bundle.json"
    path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    before = _git(repo, "rev-parse", "HEAD")

    result = dispatch_bundle(path)

    assert result["status"] == "blocked"
    assert result["terminal"] is False
    assert result["disposition"] == "legacy_validation_only"
    assert result["error_code"] == "legacy_bundle_dispatch_disabled"
    assert "validation-only" in result["blockers"][0]
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "status", "--porcelain") == ""


def test_dispatch_is_invariant_to_fake_qa_and_safe_skip_inputs(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    _git(repo, "add", "pytest.ini")
    _git(repo, "commit", "-m", "add test marker")
    bundle = _bundle(tmp_path, repo)
    bundle["completion"] = {
        "safely_skipped": {
            "reason": "unverified caller assertion",
            "artifact_path": str(tmp_path / "missing.json"),
            "artifact_sha256": "0" * 64,
        }
    }
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    before = _git(repo, "rev-parse", "HEAD")

    result = dispatch_bundle(path)

    assert result["status"] == "pending"
    assert result["qa_status"] == "not_started"
    assert result["tests_run"] == []
    assert result["completion_evidence"] == []
    assert result["commit_sha"] == ""
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "status", "--porcelain") == ""


def test_repeated_dispatch_is_idempotent_and_never_creates_a_journal(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)
    before = _git(repo, "rev-parse", "HEAD")

    first = dispatch_bundle(path)
    second = dispatch_bundle(path)

    assert first["bundle_source_sha256"] == second["bundle_source_sha256"]
    assert first["disposition"] == second["disposition"] == "external_adapter_handoff_required"
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "status", "--porcelain") == ""
    assert list((tmp_path / "portfolio-os/data/hermes_status").glob("*.execution_journal.json")) == []


def test_source_byte_hash_changes_when_only_bundle_whitespace_changes(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)
    first = dispatch_bundle(path)

    bundle = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(bundle, separators=(",", ":")) + "\n", encoding="utf-8")
    second = dispatch_bundle(path)

    assert first["bundle_canonical_sha256"] == second["bundle_canonical_sha256"]
    assert first["bundle_source_sha256"] != second["bundle_source_sha256"]


def test_pending_handoff_dispatch_cli_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_published_profit_flywheel_for_subprocess(monkeypatch)
    repo = _init_target_repo(tmp_path)
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    path = _write_bundle(tmp_path, repo)

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "hermes_cli.main",
            "portfolio-os",
            "dispatch",
            "--bundle",
            str(path),
        ],
        cwd=REPO_ROOT,
        env=_enabled_plugin_env(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode != 0
    assert '"status": "pending"' in proc.stdout
    assert '"disposition": "external_adapter_handoff_required"' in proc.stdout


def test_status_reads_result_artifact(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)
    dispatch_bundle(path)

    status = status_for_run("fixture-validation-sprint", tmp_path / "portfolio-os")

    assert status["status"] == "pending"
    assert status["disposition"] == "external_adapter_handoff_required"
    assert status["target_repo"] == "owner/target"


def test_compatibility_package_imports_current_adapter() -> None:
    from portfolio_os_adapter.contract import HERMES_TASK_BUNDLE_SCHEMA_VERSION

    assert HERMES_TASK_BUNDLE_SCHEMA_VERSION == "pos.hermes_task_bundle.v2"


def test_paperclip_usage_query_survives_schema_7_state_db_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version (version) VALUES (7);
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            model TEXT,
            started_at REAL NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            reasoning_tokens INTEGER DEFAULT 0,
            billing_provider TEXT,
            billing_base_url TEXT,
            billing_mode TEXT,
            estimated_cost_usd REAL,
            actual_cost_usd REAL,
            cost_status TEXT,
            cost_source TEXT
        );
        INSERT INTO sessions (
            id, source, model, started_at, input_tokens, output_tokens,
            cache_read_tokens, cache_write_tokens, reasoning_tokens,
            billing_provider, billing_base_url, billing_mode,
            estimated_cost_usd, actual_cost_usd, cost_status, cost_source
        )
        VALUES (
            'paperclip-session', 'paperclip-test', 'minimax/minimax-m2.7',
            1781467200.0, 101, 202, 3, 4, 5, 'minimax',
            'https://api.minimax.example/v1', 'chat_completions',
            0.0123, 0.0123, 'estimated', 'pricing_table'
        );
        """
    )
    conn.commit()
    conn.close()

    db = SessionDB(db_path)
    try:
        row = db._conn.execute(
            """
            SELECT
                COALESCE(input_tokens, 0) || char(9) ||
                COALESCE(output_tokens, 0) || char(9) ||
                COALESCE(cache_read_tokens, 0) || char(9) ||
                COALESCE(cache_write_tokens, 0) || char(9) ||
                COALESCE(reasoning_tokens, 0) || char(9) ||
                COALESCE(estimated_cost_usd, '') || char(9) ||
                COALESCE(actual_cost_usd, '') || char(9) ||
                COALESCE(cost_status, '') || char(9) ||
                COALESCE(cost_source, '') || char(9) ||
                COALESCE(billing_provider, '') || char(9) ||
                COALESCE(billing_base_url, '') || char(9) ||
                COALESCE(billing_mode, '') || char(9) ||
                COALESCE(model, '')
            FROM sessions
            WHERE id = 'paperclip-session'
            LIMIT 1
            """
        ).fetchone()
    finally:
        db.close()

    assert row is not None
    fields = row[0].split("\t")
    assert fields == [
        "101",
        "202",
        "3",
        "4",
        "5",
        "0.0123",
        "0.0123",
        "estimated",
        "pricing_table",
        "minimax",
        "https://api.minimax.example/v1",
        "chat_completions",
        "minimax/minimax-m2.7",
    ]
