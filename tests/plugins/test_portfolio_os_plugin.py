from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_state import SessionDB
from plugins.portfolio_os.contract import validate_bundle
from plugins.portfolio_os.runtime import (
    dispatch_bundle,
    dry_run_bundle,
    status_for_run,
    validate_bundle_file,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def allow_test_target_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_PORTFOLIO_OS_ALLOWED_ROOTS", str(tmp_path))


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
        "schema_version": "pos.hermes_task_bundle.v1",
        "run": {
            "run_id": run_id,
            "generated_at": "2026-06-01T00:00:00+00:00",
            "portfolio_os_commit": "fixture",
            "paperclip_execution_id": "pc-fixture",
            "snapshot_hash": "fixture",
            "mandate_hash": "fixture",
            "execution_mandate_hash": "fixture",
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


def test_validate_bundle_accepts_valid_bundle(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)

    assert validate_bundle_file(path) == []


def test_plugin_cli_command_accepts_portfolio_os_namespace(tmp_path: Path) -> None:
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


def test_dispatch_docs_only_validation_sprint_commits_result_artifact(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)

    result = dispatch_bundle(path)

    assert result["status"] == "completed"
    assert result["internet_pipes"]["readiness"] == "promising"
    assert result["internet_pipes"]["missing_stations"] == ["differentiation"]
    assert result["commit_sha"]
    assert result["pushed_to_origin"] is False
    assert (repo / "docs/business_plan.md").exists()
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert "Fixture Target" in readme
    assert "Portfolio-OS Business Value Hypothesis" in readme
    assert "Internet Pipes: score=63.50, readiness=promising, missing_stations=differentiation" in readme
    result_path = tmp_path / "portfolio-os/data/hermes_results/fixture-validation-sprint.json"
    assert result_path.exists()
    assert json.loads(result_path.read_text(encoding="utf-8"))["commit_sha"] == result["commit_sha"]
    log_path = tmp_path / "portfolio-os/data/hermes_logs/fixture-validation-sprint.log"
    assert "internet_pipes=" in log_path.read_text(encoding="utf-8")


def test_dispatch_refuses_dirty_target_repository(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    (repo / "unrelated.txt").write_text("uncommitted\n", encoding="utf-8")
    path = _write_bundle(tmp_path, repo)
    before = _git(repo, "rev-parse", "HEAD")

    result = dispatch_bundle(path)

    assert result["status"] == "blocked"
    assert result["blockers"] == ["Target repository must be clean before dispatch."]
    assert _git(repo, "rev-parse", "HEAD") == before
    assert not (repo / "docs/business_plan.md").exists()


def test_dispatch_blocks_secret_like_content_before_commit(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    bundle = _bundle(tmp_path, repo)
    bundle["tasks"] = [
        {
            "id": "secret-doc",
            "title": "Credential notes",
            "type": "docs",
            "instructions": 'api_key = "abcdefghijklmnopqrstuvwx"',
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
    before = _git(repo, "rev-parse", "HEAD")

    result = dispatch_bundle(path)

    assert result["status"] == "blocked"
    assert result["blockers"] == ["Secret-like content refused: docs/execution_notes.md"]
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_status_reads_result_artifact(tmp_path: Path) -> None:
    repo = _init_target_repo(tmp_path)
    path = _write_bundle(tmp_path, repo)
    dispatch_bundle(path)

    status = status_for_run("fixture-validation-sprint", tmp_path / "portfolio-os")

    assert status["status"] == "completed"
    assert status["target_repo"] == "owner/target"


def test_compatibility_package_imports_current_adapter() -> None:
    from portfolio_os_adapter.contract import HERMES_TASK_BUNDLE_SCHEMA_VERSION

    assert HERMES_TASK_BUNDLE_SCHEMA_VERSION == "pos.hermes_task_bundle.v1"


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
