# SPDX-License-Identifier: Proprietary
# Copyright (C) 2026 ProtocolWarden
"""Launch anchoring: every Console-launched CLI (claude/codex/aider) anchors at
its repo's owning manifest via `cl session start` (no hardcoded CL_ANCHOR=cwd),
and the cross-repo group tab cds into PlatformManifest (not the workspace root)."""

from __future__ import annotations

from pathlib import Path

from operator_console.bootstrap import (
    get_aider_command,
    get_claude_command,
    get_codex_command,
)
from operator_console.launcher import _multi_pane_block


def _console_dir(tmp_path: Path) -> Path:
    cd = tmp_path / "console"
    (cd / "config" / "profiles").mkdir(parents=True)
    return cd


def _script_of(cmd: str) -> str:
    # wrapper commands look like: bash '<script-path>'
    return Path(cmd.split("'")[1]).read_text(encoding="utf-8")


def test_all_three_cli_wrappers_anchor_via_cl_session_start(tmp_path, monkeypatch):
    # CL_HOME points at a fake CL clone with an executable `cl` so the prelude
    # bakes a concrete path (machine-independent).
    cl_home = tmp_path / "ContextLifecycle"
    cl_bin = cl_home / "bin" / "cl"
    cl_bin.parent.mkdir(parents=True)
    cl_bin.write_text("#!/usr/bin/env bash\n")
    cl_bin.chmod(0o755)
    monkeypatch.setenv("CL_HOME", str(cl_home))

    console_dir = _console_dir(tmp_path)
    profile = {"name": "platform", "repo_root": str(tmp_path / "repo")}
    for builder in (get_claude_command, get_codex_command, get_aider_command):
        cmd = builder(profile, tmp_path / "repo", console_dir=console_dir, session_key="platform")
        script = _script_of(cmd)
        # Prelude bakes the resolved cl path, then calls `cl session start`.
        assert "session start" in script, f"{builder.__name__} missing anchor prelude"
        assert str(cl_bin) in script, f"{builder.__name__} did not bake the cl path"
        # No hardcoded cwd-as-anchor (the old, wrong behavior).
        assert "export CL_ANCHOR='" not in script


def test_prelude_is_inert_when_cl_unavailable(tmp_path, monkeypatch):
    # No CL_HOME, no settings.json, no cl on PATH → prelude is a comment, never
    # a broken command.
    from operator_console.bootstrap import _cl_anchor_prelude

    monkeypatch.delenv("CL_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", "")
    prelude = _cl_anchor_prelude()
    assert prelude.lstrip().startswith("#")
    assert "session start" not in prelude


def test_group_tab_anchors_at_platform_manifest(tmp_path):
    console_dir = _console_dir(tmp_path)
    profiles = [
        {"name": "a", "repo_root": str(tmp_path / "A")},
        {"name": "b", "repo_root": str(tmp_path / "B")},
    ]
    block = _multi_pane_block(profiles, console_dir=console_dir, tab_name="platform")
    assert "PlatformManifest" in block
    assert "cd '" in block and "/PlatformManifest'" in block
