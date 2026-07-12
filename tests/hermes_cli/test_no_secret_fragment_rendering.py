"""Regression guards for zero-fragment credential displays and logs."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DISPLAY_FILES = [
    "agent/agent_init.py",
    "cli.py",
    "gateway/config.py",
    "gateway/platforms/yuanbao.py",
    "hermes_cli/dingtalk_auth.py",
    "hermes_cli/mcp_config.py",
    "hermes_cli/memory_setup.py",
    "hermes_cli/model_setup_flows.py",
    "hermes_cli/setup_whatsapp_cloud.py",
]
SECRET_FRAGMENT = re.compile(
    r"\b(?:api_?key|existing_key|token|secret|app_key)\s*\[\s*(?::|-)",
    re.IGNORECASE,
)


def test_credential_display_sites_never_slice_secret_fragments() -> None:
    offenders: list[str] = []
    for relative in DISPLAY_FILES:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for match in SECRET_FRAGMENT.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{relative}:{line}:{match.group(0)}")

    assert offenders == [], (
        "Credential UI/log sites must report configured/not-set or a one-way "
        f"fingerprint, never raw prefix/suffix fragments: {offenders}"
    )
