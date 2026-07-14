from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Mapping


HERMES_TASK_BUNDLE_SCHEMA_VERSION = "pos.hermes_task_bundle.v2"
LEGACY_HERMES_TASK_BUNDLE_SCHEMA_VERSION = "pos.hermes_task_bundle.v1"
PROFIT_FLYWHEEL_SCHEMA_VERSION = "profit-flywheel.v2"
PROFIT_FLYWHEEL_CONTRACT_ID = "profit-flywheel"
DEFAULT_PROFIT_FLYWHEEL_CONTRACT_PATH = Path(
    "/Users/mnm/Documents/Github/portfolio-os/contracts/profit-flywheel.v2.json"
)
DEFAULT_PROFIT_FLYWHEEL_SCHEMA_PATH = Path(
    "/Users/mnm/Documents/Github/portfolio-os/contracts/profit-flywheel.v2.schema.json"
)
DEFAULT_PROVIDER_POLICY_PATH = Path("/Users/mnm/Documents/Github/paperclip/config/provider-policy.v2.json")
DEFAULT_PROVIDER_POLICY_SCHEMA_PATH = Path(
    "/Users/mnm/Documents/Github/paperclip/config/provider-policy.v2.schema.json"
)
# Frozen Portfolio-OS/Paperclip trust roots.  Environment variables and task
# bundles must agree with these values; they are not allowed to redefine them.
PINNED_PROFIT_FLYWHEEL_CONTRACT_SHA256 = (
    "9222ed478724c230731ebcced6809ff6b4a4bb7dc934fddb2882ae7c92501723"
)
PINNED_PROFIT_FLYWHEEL_CONTRACT_SCHEMA_SHA256 = (
    "6ac1af81be0de807f51dbba786b73897f114244c1616abee5b3f41a6dbfac09b"
)
PINNED_PROFIT_FLYWHEEL_RUN_SCHEMA_SHA256 = (
    "ba26611e26941535a29e7faf431e04da3fd05367b2d93e6b8398bebc73872481"
)
PINNED_POS_DISPATCH_SCHEMA_SHA256 = (
    "1e9a0f8bc76a0d0f3e54c4144ccfadc9907daf59a815480711497188f05340a6"
)
PINNED_POS_LEARNING_RECEIPT_SCHEMA_SHA256 = (
    "e63c3700eae9baa2d75b31d2a222cc7df474d8fbb72165ecddf03d9211ecf267"
)
PINNED_POS_NEXT_RESEARCH_AUTHORITY_SCHEMA_SHA256 = (
    "8ff5e8b0cad03f4639db23cb994353542493cb6ad3a4c041311b2b374b2bbed7"
)
PINNED_PAPERCLIP_RESEARCH_PLAN_SCHEMA_SHA256 = (
    "88faae2962f76f4bf2bfce022cf25b14d9891e836a2b68cea533b3d749f111f4"
)
PINNED_STAGE_WORK_RESULT_SCHEMA_SHA256 = (
    "beff2e8e4d31413329a73e6891d1c9104e004a2a4e621192d39845ff08019fba"
)
PINNED_STAGE_EXECUTION_SCHEMA_SHA256 = (
    "fb080707e7d65bb17664e494dea765fa4c7018c42a9317d188da8da6be03b6b2"
)
PINNED_TEST_EXECUTION_RESULT_SCHEMA_SHA256 = (
    "3896d169ef45baae7c19dba9cfb0bc1d2fee18cbc2018d3c734ef23815f896d2"
)
PINNED_INDEPENDENT_REVIEW_RESULT_SCHEMA_SHA256 = (
    "d90769477297810c8536624068fc3af1864d059a6b6d658e9648a0ae53c941af"
)
PINNED_EXECUTION_GOLDEN_VECTORS_SHA256 = (
    "4ad38f8e0174f1acd0d370837a6c6cdfc61f3bc7f32b7a63c085b973e66eb272"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
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
    schema_version = str(payload.get("schema_version", "")).strip()
    if schema_version not in {
        HERMES_TASK_BUNDLE_SCHEMA_VERSION,
        LEGACY_HERMES_TASK_BUNDLE_SCHEMA_VERSION,
    }:
        errors.append(
            "schema_version must equal "
            f"{HERMES_TASK_BUNDLE_SCHEMA_VERSION} or {LEGACY_HERMES_TASK_BUNDLE_SCHEMA_VERSION}"
        )
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
        if schema_version == HERMES_TASK_BUNDLE_SCHEMA_VERSION and task_type != "QA":
            expected_files = _string_list(task.get("files_expected"))
            if not expected_files:
                errors.append(f"tasks[{index}].files_expected must declare completion evidence")
            for relative in expected_files:
                candidate = Path(relative)
                if candidate.is_absolute() or ".." in candidate.parts:
                    errors.append(f"tasks[{index}].files_expected contains an unsafe path: {relative}")
            if not _string_list(task.get("acceptance_criteria")):
                errors.append(f"tasks[{index}].acceptance_criteria must not be empty")
        task_text = json.dumps(task, sort_keys=True).lower()
        for forbidden in FORBIDDEN_OPERATIONS:
            if forbidden in task_text:
                errors.append(f"tasks[{index}] references forbidden operation {forbidden}")

    if schema_version == HERMES_TASK_BUNDLE_SCHEMA_VERSION:
        _validate_execution_governance(payload, tasks, errors)

    safety = _mapping(payload.get("safety"))
    if safety.get("destructive_ops_allowed") is not False:
        errors.append("safety.destructive_ops_allowed must be false")
    if safety.get("secrets_scan_required") is not True:
        errors.append("safety.secrets_scan_required must be true")
    missing = FORBIDDEN_OPERATIONS - {str(item) for item in _list(safety.get("forbidden_operations"))}
    if missing:
        errors.append(f"safety.forbidden_operations missing {sorted(missing)}")
    _validate_output_paths(payload, errors)
    return errors


def is_execution_bundle(payload: Mapping[str, Any]) -> bool:
    """Return whether a bundle is the governance-bound executable v2 form."""
    return payload.get("schema_version") == HERMES_TASK_BUNDLE_SCHEMA_VERSION


def _required_text(container: Mapping[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = str(container.get(key, "") or "").strip()
    if not value:
        errors.append(f"{path}.{key} is required")
    return value


def _positive_int(container: Mapping[str, Any], key: str, path: str, errors: list[str]) -> int | None:
    value = container.get(key)
    if isinstance(value, bool):
        value = None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 0
    if parsed <= 0:
        errors.append(f"{path}.{key} must be a positive integer")
        return None
    return parsed


def _nonnegative_int(container: Mapping[str, Any], key: str, path: str, errors: list[str]) -> int | None:
    value = container.get(key)
    if isinstance(value, bool):
        value = None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = -1
    if parsed < 0:
        errors.append(f"{path}.{key} must be a nonnegative integer")
        return None
    return parsed


def _required_env(name: str, errors: list[str]) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        errors.append(f"{name} must pin executable bundles")
    return value


def _require_frozen_pin_env(name: str, expected: str, errors: list[str]) -> None:
    """Require the caller's duplicate pin to equal the compiled trust root."""
    observed = _required_env(name, errors)
    if observed and observed != expected:
        errors.append(f"{name} does not match the frozen Hermes trust root")


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _load_json_object(path: Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _validate_frozen_schema_file(
    path: Path,
    *,
    label: str,
    expected_sha256: str,
    errors: list[str],
) -> None:
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        errors.append(f"frozen {label} SHA-256 pin is missing or malformed")
        return
    actual = _sha256_file(path)
    if actual is None:
        errors.append(f"frozen {label} is unreadable: {path}")
    elif actual != expected_sha256:
        errors.append(f"frozen {label} SHA-256 does not match schema bytes")


def _validate_frozen_profit_flywheel_schemas(
    manifest: Mapping[str, Any],
    *,
    contract_path: Path,
    errors: list[str],
) -> None:
    """Verify every schema needed to consume or emit flywheel artifacts."""
    bindings = _mapping(manifest.get("artifact_schemas"))
    expected_bindings = (
        (
            "run_receipt",
            "profit-flywheel.run.v2",
            "contracts/profit-flywheel.run.v2.schema.json",
            PINNED_PROFIT_FLYWHEEL_RUN_SCHEMA_SHA256,
        ),
        (
            "dispatch",
            "pos.dispatch.v2",
            "contracts/pos.dispatch.v2.schema.json",
            PINNED_POS_DISPATCH_SCHEMA_SHA256,
        ),
        (
            "learning_receipt",
            "pos.learning_receipt.v2",
            "contracts/pos.learning_receipt.v2.schema.json",
            PINNED_POS_LEARNING_RECEIPT_SCHEMA_SHA256,
        ),
        (
            "next_research_authority",
            "pos.next_research_authorization.v1",
            "contracts/pos.next_research_authorization.v1.schema.json",
            PINNED_POS_NEXT_RESEARCH_AUTHORITY_SCHEMA_SHA256,
        ),
        (
            "research_plan",
            "paperclip.research_plan.v2",
            "contracts/paperclip.research_plan.v2.schema.json",
            PINNED_PAPERCLIP_RESEARCH_PLAN_SCHEMA_SHA256,
        ),
        (
            "stage_work_result",
            "paperclip.profit_flywheel_stage_work_result.v1",
            "contracts/stage-work-result.v1.schema.json",
            PINNED_STAGE_WORK_RESULT_SCHEMA_SHA256,
        ),
        (
            "stage_execution",
            "paperclip.profit_flywheel_stage_execution.v2",
            "contracts/stage-execution.v2.schema.json",
            PINNED_STAGE_EXECUTION_SCHEMA_SHA256,
        ),
        (
            "test_execution_result",
            "paperclip.test_execution_result.v1",
            "contracts/test-execution-result.v1.schema.json",
            PINNED_TEST_EXECUTION_RESULT_SCHEMA_SHA256,
        ),
        (
            "independent_review_result",
            "paperclip.independent_review_result.v1",
            "contracts/independent-review-result.v1.schema.json",
            PINNED_INDEPENDENT_REVIEW_RESULT_SCHEMA_SHA256,
        ),
    )
    expected_names = {name for name, _, _, _ in expected_bindings}
    if set(bindings) != expected_names:
        errors.append("pinned profit-flywheel artifact_schemas must bind every canonical cross-plane schema")

    contract_root = contract_path.parent.parent
    for name, schema_version, relative_path, expected_sha256 in expected_bindings:
        binding = _mapping(bindings.get(name))
        label = f"profit-flywheel {name} schema"
        if binding.get("schema_version") != schema_version:
            errors.append(f"pinned {label} has the wrong schema_version")
        if binding.get("path") != relative_path:
            errors.append(f"pinned {label} has the wrong path")
        if binding.get("sha256") != expected_sha256:
            errors.append(f"pinned {label} SHA-256 does not match the frozen Hermes trust root")
        _validate_frozen_schema_file(
            contract_root / relative_path,
            label=label,
            expected_sha256=expected_sha256,
            errors=errors,
        )

    vectors = _mapping(manifest.get("artifact_vectors"))
    execution_vectors = _mapping(vectors.get("execution"))
    if set(vectors) != {"execution"}:
        errors.append("pinned profit-flywheel artifact_vectors must bind exactly execution")
    if execution_vectors.get("schema_version") != "paperclip.profit_flywheel_execution_golden_vectors.v1":
        errors.append("pinned execution vectors have the wrong schema_version")
    if execution_vectors.get("path") != "contracts/execution-golden-vectors.v1.json":
        errors.append("pinned execution vectors have the wrong path")
    if execution_vectors.get("sha256") != PINNED_EXECUTION_GOLDEN_VECTORS_SHA256:
        errors.append("pinned execution vectors SHA-256 does not match the frozen Hermes trust root")
    vector_path = contract_root / "contracts/execution-golden-vectors.v1.json"
    _validate_frozen_schema_file(
        vector_path,
        label="profit-flywheel execution golden vectors",
        expected_sha256=PINNED_EXECUTION_GOLDEN_VECTORS_SHA256,
        errors=errors,
    )
    vector_payload = _load_json_object(vector_path)
    if (
        vector_payload is None
        or vector_payload.get("schema_version")
        != "paperclip.profit_flywheel_execution_golden_vectors.v1"
        or set(vector_payload) != {"schema_version", "valid", "invalid"}
    ):
        errors.append("pinned execution golden vectors have an invalid identity or shape")


def _validate_pinned_file(
    binding: Mapping[str, Any],
    *,
    binding_path: str,
    expected_path: Path,
    expected_schema_path: Path,
    expected_sha256: str,
    expected_schema_sha256: str,
    errors: list[str],
) -> tuple[Path | None, Path | None]:
    raw_path = _required_text(binding, "path", binding_path, errors)
    raw_schema_path = _required_text(binding, "schema_path", binding_path, errors)
    binding_sha = _required_text(binding, "sha256", binding_path, errors)
    binding_schema_sha = _required_text(binding, "schema_sha256", binding_path, errors)
    path = Path(raw_path).expanduser().resolve(strict=False) if raw_path else None
    schema_path = Path(raw_schema_path).expanduser().resolve(strict=False) if raw_schema_path else None
    if path is not None and path != expected_path.resolve(strict=False):
        errors.append(f"{binding_path}.path does not match the pinned manifest path")
    if schema_path is not None and schema_path != expected_schema_path.resolve(strict=False):
        errors.append(f"{binding_path}.schema_path does not match the pinned schema path")
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        errors.append(f"expected {binding_path} SHA-256 pin is missing or malformed")
    elif binding_sha != expected_sha256:
        errors.append(f"{binding_path}.sha256 does not match the expected SHA-256")
    if not SHA256_PATTERN.fullmatch(expected_schema_sha256):
        errors.append(f"expected {binding_path} schema SHA-256 pin is missing or malformed")
    elif binding_schema_sha != expected_schema_sha256:
        errors.append(f"{binding_path}.schema_sha256 does not match the expected schema SHA-256")
    if path is not None:
        actual = _sha256_file(path)
        if actual is None:
            errors.append(f"{binding_path}.path is unreadable")
        elif binding_sha != actual:
            errors.append(f"{binding_path}.sha256 does not match the manifest bytes")
    if schema_path is not None:
        actual_schema = _sha256_file(schema_path)
        if actual_schema is None:
            errors.append(f"{binding_path}.schema_path is unreadable")
        elif binding_schema_sha != actual_schema:
            errors.append(f"{binding_path}.schema_sha256 does not match the schema bytes")
    return path, schema_path


def _validate_execution_governance(
    payload: Mapping[str, Any],
    tasks: list[Any],
    errors: list[str],
) -> None:
    governance = _mapping(payload.get("governance"))
    if governance.get("execution_authority") != "paperclip_control_plane":
        errors.append("governance.execution_authority must equal paperclip_control_plane")

    contract = _mapping(governance.get("profit_flywheel_contract"))
    if contract.get("id") != PROFIT_FLYWHEEL_CONTRACT_ID:
        errors.append(f"governance.profit_flywheel_contract.id must equal {PROFIT_FLYWHEEL_CONTRACT_ID}")
    if contract.get("schema_version") != PROFIT_FLYWHEEL_SCHEMA_VERSION:
        errors.append(
            f"governance.profit_flywheel_contract.schema_version must equal {PROFIT_FLYWHEEL_SCHEMA_VERSION}"
        )
    expected_contract_path = Path(
        os.environ.get("PAPERCLIP_PROFIT_FLYWHEEL_CONTRACT_PATH", str(DEFAULT_PROFIT_FLYWHEEL_CONTRACT_PATH))
    )
    expected_contract_schema_path = Path(
        os.environ.get("PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_PATH", str(DEFAULT_PROFIT_FLYWHEEL_SCHEMA_PATH))
    )
    _require_frozen_pin_env(
        "PAPERCLIP_PROFIT_FLYWHEEL_SHA256",
        PINNED_PROFIT_FLYWHEEL_CONTRACT_SHA256,
        errors,
    )
    _require_frozen_pin_env(
        "PAPERCLIP_PROFIT_FLYWHEEL_SCHEMA_SHA256",
        PINNED_PROFIT_FLYWHEEL_CONTRACT_SCHEMA_SHA256,
        errors,
    )
    contract_path, _ = _validate_pinned_file(
        contract,
        binding_path="governance.profit_flywheel_contract",
        expected_path=expected_contract_path,
        expected_schema_path=expected_contract_schema_path,
        expected_sha256=PINNED_PROFIT_FLYWHEEL_CONTRACT_SHA256,
        expected_schema_sha256=PINNED_PROFIT_FLYWHEEL_CONTRACT_SCHEMA_SHA256,
        errors=errors,
    )
    contract_manifest = _load_json_object(contract_path) if contract_path is not None else None
    if contract_manifest is None:
        errors.append("governance.profit_flywheel_contract.path must contain a JSON object")
    else:
        if contract_manifest.get("contract_id") != PROFIT_FLYWHEEL_CONTRACT_ID:
            errors.append("pinned profit-flywheel manifest has the wrong contract_id")
        if contract_manifest.get("schema_version") != PROFIT_FLYWHEEL_SCHEMA_VERSION:
            errors.append("pinned profit-flywheel manifest has the wrong schema_version")
        if contract_path is not None:
            _validate_frozen_profit_flywheel_schemas(
                contract_manifest,
                contract_path=contract_path,
                errors=errors,
            )

    policy = _mapping(governance.get("provider_policy"))
    _required_text(policy, "policy_id", "governance.provider_policy", errors)
    _required_text(policy, "revision", "governance.provider_policy", errors)
    if policy.get("schema_version") != "provider-policy.v2":
        errors.append("governance.provider_policy.schema_version must equal provider-policy.v2")
    expected_policy_path = Path(
        os.environ.get("PAPERCLIP_PROVIDER_POLICY_PATH", str(DEFAULT_PROVIDER_POLICY_PATH))
    )
    expected_policy_schema_path = Path(
        os.environ.get("PAPERCLIP_PROVIDER_POLICY_SCHEMA_PATH", str(DEFAULT_PROVIDER_POLICY_SCHEMA_PATH))
    )
    policy_path, _ = _validate_pinned_file(
        policy,
        binding_path="governance.provider_policy",
        expected_path=expected_policy_path,
        expected_schema_path=expected_policy_schema_path,
        expected_sha256=_required_env("PAPERCLIP_PROVIDER_POLICY_SHA256", errors),
        expected_schema_sha256=_required_env("PAPERCLIP_PROVIDER_POLICY_SCHEMA_SHA256", errors),
        errors=errors,
    )
    policy_manifest = _load_json_object(policy_path) if policy_path is not None else None
    if policy_manifest is None:
        errors.append("governance.provider_policy.path must contain a JSON object")
    elif policy_manifest.get("schemaVersion") != "provider-policy.v2":
        errors.append("pinned provider policy has the wrong schemaVersion")

    route = _mapping(governance.get("resolved_route"))
    route_id = _required_text(route, "route_id", "governance.resolved_route", errors)
    provider = _required_text(route, "provider", "governance.resolved_route", errors)
    model = _required_text(route, "model", "governance.resolved_route", errors)
    model_version = _required_text(route, "model_version", "governance.resolved_route", errors)
    for field, actual, env_name in [
        ("route_id", route_id, "PAPERCLIP_RESOLVED_ROUTE_ID"),
        ("provider", provider, "PAPERCLIP_RESOLVED_PROVIDER"),
        ("model", model, "PAPERCLIP_RESOLVED_MODEL"),
        ("model_version", model_version, "PAPERCLIP_RESOLVED_MODEL_VERSION"),
    ]:
        expected = _required_env(env_name, errors)
        if expected and actual != expected:
            errors.append(f"governance.resolved_route.{field} does not match {env_name}")
    if policy_manifest is not None:
        manifest_route = _mapping(_mapping(policy_manifest.get("routes")).get(route_id))
        manifest_model = _mapping(manifest_route.get("model"))
        if not manifest_route:
            errors.append("governance.resolved_route.route_id is absent from the pinned provider policy")
        else:
            if manifest_route.get("provider") != provider:
                errors.append("governance.resolved_route.provider does not match the pinned route")
            if manifest_model.get("kind") != "exact" or manifest_model.get("value") != model:
                errors.append("governance.resolved_route.model does not match the pinned exact route")
            if manifest_model.get("version") != model_version:
                errors.append("governance.resolved_route.model_version does not match the pinned route")

    execution = _mapping(payload.get("execution"))
    _required_text(execution, "correlation_id", "execution", errors)
    issue_id = _required_text(execution, "issue_id", "execution", errors)
    stage_id = _required_text(execution, "stage_id", "execution", errors)
    budgets = _mapping(execution.get("budgets"))
    max_tasks = _positive_int(budgets, "max_tasks", "execution.budgets", errors)
    for field in [
        "turns",
        "context_chars",
        "output_chars",
        "token_limit",
        "tool_output_bytes",
        "tool_output_lines",
        "tool_output_line_chars",
    ]:
        _positive_int(budgets, field, "execution.budgets", errors)
    max_escalations = _nonnegative_int(budgets, "max_escalations", "execution.budgets", errors)
    if max_escalations not in {None, 0}:
        errors.append("execution.budgets.max_escalations must be 0; route escalation belongs to the control plane")
    if max_tasks is not None and len(tasks) > max_tasks:
        errors.append("tasks exceed execution.budgets.max_tasks")
    issue_ids = {str(item).strip() for item in _list(_mapping(payload.get("paperclip")).get("issue_ids"))}
    if issue_id and issue_id not in issue_ids:
        errors.append("execution.issue_id must be present in paperclip.issue_ids")

    target = _mapping(payload.get("target"))
    push_policy = _mapping(target.get("push_policy"))
    if stage_id != "release" and (
        push_policy.get("push_to_origin") or push_policy.get("create_pr") or not push_policy.get("no_push")
    ):
        errors.append("non-release execution stages must set push_policy.no_push and disable push/create_pr")
    if stage_id == "release":
        transition = _mapping(execution.get("release_transition"))
        if transition.get("from") != "qa" or transition.get("to") != "release":
            errors.append("execution.release_transition must declare qa -> release")
        if transition.get("trigger") != "validated_artifact_completion":
            errors.append("execution.release_transition.trigger must equal validated_artifact_completion")
        if transition.get("guard") != "qa_passed_and_artifact_backed":
            errors.append("execution.release_transition.guard must equal qa_passed_and_artifact_backed")
        guards = set(_string_list(execution.get("release_stage_guards")))
        required_guards = {"artifact_backed_completion", "qa_passed"}
        if not required_guards.issubset(guards):
            errors.append(f"execution.release_stage_guards missing {sorted(required_guards - guards)}")
        release_evidence = _mapping(execution.get("release_completion_evidence"))
        for key in ["artifact_url_or_commit", "artifact_hash", "release_status"]:
            _required_text(release_evidence, key, "execution.release_completion_evidence", errors)



def _validate_output_paths(payload: Mapping[str, Any], errors: list[str]) -> None:
    outputs = _mapping(payload.get("outputs"))
    output_roots_raw = os.environ.get(
        "HERMES_PORTFOLIO_OS_OUTPUT_ROOTS",
        "/Users/mnm/Documents/Github/portfolio-os/data",
    )
    output_roots = [
        Path(raw).expanduser().resolve(strict=False)
        for raw in output_roots_raw.split(os.pathsep)
        if raw.strip()
    ]
    for key in ["result_path", "patch_plan_path", "execution_log_path"]:
        raw = _required_text(outputs, key, "outputs", errors)
        if raw:
            resolved = Path(raw).expanduser().resolve(strict=False)
            if not any(_inside(resolved, root) for root in output_roots):
                errors.append(f"outputs.{key} is outside HERMES_PORTFOLIO_OS_OUTPUT_ROOTS")
    result_raw = str(outputs.get("result_path", "")).strip()
    if result_raw:
        journal = Path(result_raw).expanduser().resolve(strict=False).parent.parent / "hermes_status"
        if not any(_inside(journal.resolve(strict=False), root) for root in output_roots):
            errors.append("derived execution journal path is outside HERMES_PORTFOLIO_OS_OUTPUT_ROOTS")


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
