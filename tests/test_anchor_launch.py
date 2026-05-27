# SPDX-License-Identifier: Proprietary
# Copyright (C) 2026 ProtocolWarden
"""Launch anchoring: OC-launched Claude sessions must export CL_ANCHOR, and the
cross-repo group tab must anchor at PlatformManifest (not the bare workspace root)."""

from __future__ import annotations

from pathlib import Path

from operator_console.bootstrap import get_claude_command
from operator_console.launcher import _multi_pane_block


def _console_dir(tmp_path: Path) -> Path:
    cd = tmp_path / "console"
    (cd / "config" / "profiles").mkdir(parents=True)
    return cd


def test_claude_wrapper_exports_cl_anchor_equal_to_cwd(tmp_path):
    console_dir = _console_dir(tmp_path)
    anchor = tmp_path / "PlatformManifest"
    cmd = get_claude_command(
        {"name": "platform", "repo_root": str(tmp_path / "repo")},
        tmp_path / "repo",
        console_dir=console_dir,
        session_key="platform",
        claude_cwd=anchor,
    )
    # cmd == "bash '<script>'" — read the generated wrapper
    script_path = cmd.split("'")[1]
    script = Path(script_path).read_text(encoding="utf-8")
    assert f"export CL_ANCHOR='{anchor.resolve()}'" in script


def test_group_tab_anchors_at_platform_manifest(tmp_path):
    console_dir = _console_dir(tmp_path)
    profiles = [
        {"name": "a", "repo_root": str(tmp_path / "A")},
        {"name": "b", "repo_root": str(tmp_path / "B")},
    ]
    block = _multi_pane_block(profiles, console_dir=console_dir, tab_name="platform")
    # Panes cd into PlatformManifest, not the bare ~/Documents/GitHub root.
    assert "PlatformManifest" in block
    assert "cd '" in block and "/PlatformManifest'" in block
