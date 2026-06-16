# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""Tests for the Fleet Capabilities context section (bootstrap capability
read-model consumer). The console reads PlatformManifest's capabilities.yaml
directly (PyYAML, no platform_manifest/repograph import) and renders a grouped,
fail-soft legibility section into the compiled startup context."""

from __future__ import annotations

from pathlib import Path

from operator_console.bootstrap import (
    _find_capabilities_file,
    _format_capability_scope,
    _render_capabilities_section,
    build_resume_prompt,
)

_REL = Path("src/platform_manifest/data/capabilities.yaml")

_REGISTRY = """schema_kind: capabilities
schema_version: 1.0.0
capabilities:
  - action_id: repo_health_audit
    name: Repo Health Audit
    owner_repo_id: custodian
    target_scope:
      kind: repo_set
      selector:
        visibility: public
    risk: read_only
    visibility: public
  - action_id: board_unblock
    name: Board Unblock
    owner_repo_id: operations_center
    target_scope:
      kind: fleet
    risk: mutates_fleet
    routing:
      preferred_lane: maintenance
    visibility: public
"""


def _write_registry(root: Path, text: str = _REGISTRY) -> Path:
    path = root / _REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- locator -----------------------------------------------------------------

def test_finds_registry_in_repo(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    assert _find_capabilities_file(tmp_path) == tmp_path / _REL


def test_finds_registry_in_sibling_platform_manifest(tmp_path: Path) -> None:
    # Anchored at some OTHER repo; PlatformManifest is a sibling checkout.
    pm = tmp_path / "PlatformManifest"
    _write_registry(pm)
    other = tmp_path / "OperatorConsole"
    other.mkdir()
    assert _find_capabilities_file(other) == pm / _REL


def test_missing_registry_returns_none(tmp_path: Path) -> None:
    assert _find_capabilities_file(tmp_path) is None


# --- scope rendering (locked trichotomy) -------------------------------------

def test_scope_repo() -> None:
    assert _format_capability_scope({"kind": "repo", "repo_id": "custodian"}) == "repo(custodian)"


def test_scope_repo_set() -> None:
    assert _format_capability_scope(
        {"kind": "repo_set", "selector": {"visibility": "public"}}
    ) == "repo_set(visibility=public)"


def test_scope_fleet() -> None:
    assert _format_capability_scope({"kind": "fleet"}) == "fleet"


# --- section rendering -------------------------------------------------------

def test_section_groups_by_owner_sorted_with_optional_lane(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    section = _render_capabilities_section(tmp_path)
    assert section is not None
    assert "## Fleet Capabilities" in section
    # grouped by owner, owners sorted (custodian before operations_center)
    assert section.index("**custodian**") < section.index("**operations_center**")
    # read_only cap has no routing → no lane suffix
    assert "Repo Health Audit — repo_set(visibility=public) · read_only" in section
    assert "Repo Health Audit — repo_set(visibility=public) · read_only · lane" not in section
    # fleet cap with routing → lane shown
    assert "Board Unblock — fleet · mutates_fleet · lane: maintenance" in section


def test_private_capability_excluded(tmp_path: Path) -> None:
    _write_registry(tmp_path, _REGISTRY + """  - action_id: secret_op
    name: Secret Op
    owner_repo_id: video_foundry
    target_scope:
      kind: fleet
    risk: read_only
    visibility: private
""")
    section = _render_capabilities_section(tmp_path)
    assert section is not None
    assert "Secret Op" not in section
    assert "video_foundry" not in section


# --- fail-soft (never block context compilation) -----------------------------

def test_no_registry_returns_none(tmp_path: Path) -> None:
    assert _render_capabilities_section(tmp_path) is None


def test_malformed_yaml_returns_none(tmp_path: Path) -> None:
    _write_registry(tmp_path, "capabilities: [unclosed\n  - : :")
    assert _render_capabilities_section(tmp_path) is None


def test_capabilities_not_a_list_returns_none(tmp_path: Path) -> None:
    _write_registry(tmp_path, "schema_kind: capabilities\ncapabilities: not-a-list\n")
    assert _render_capabilities_section(tmp_path) is None


def test_empty_capabilities_returns_none(tmp_path: Path) -> None:
    _write_registry(tmp_path, "schema_kind: capabilities\ncapabilities: []\n")
    assert _render_capabilities_section(tmp_path) is None


# --- integration with the full context build ---------------------------------

def test_build_resume_prompt_includes_capabilities(tmp_path: Path) -> None:
    console = tmp_path / ".console"
    console.mkdir()
    (console / "task.md").write_text("Do the thing", encoding="utf-8")
    _write_registry(tmp_path)
    prompt = build_resume_prompt(tmp_path)
    assert "## Fleet Capabilities" in prompt
    assert "Board Unblock" in prompt


def test_build_resume_prompt_safe_without_registry(tmp_path: Path) -> None:
    console = tmp_path / ".console"
    console.mkdir()
    (console / "task.md").write_text("Do the thing", encoding="utf-8")
    prompt = build_resume_prompt(tmp_path)
    assert "## Fleet Capabilities" not in prompt
    assert "Do the thing" in prompt
