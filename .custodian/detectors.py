# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""OperatorConsole OS symmetry detectors for Custodian.

  OS-SYM1  Bare package manager call in Python — code calls subprocess with
            apt-get/apt/pacman/dpkg directly without routing through
            _detect_pkg_manager() or pm_install()/detect_pm() first.

  OS-SYM1S Bare package manager call in shell — tools/*.sh calls apt-get/apt/
            pacman/dpkg directly without a detect_pm() guard in the same file.
"""
from __future__ import annotations

import re
from pathlib import Path

from custodian.audit_kit.detector import AuditContext, Detector, DetectorResult, HIGH


_SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__"}

def _py_files(root: Path) -> list[Path]:
    return [
        p for p in root.rglob("*.py")
        if not any(part in _SKIP_DIRS for part in p.parts)
    ]

def _sh_files(root: Path) -> list[Path]:
    return [
        p for p in root.rglob("*.sh")
        if not any(part in _SKIP_DIRS for part in p.parts)
    ]

def _file_text(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""

def _non_comment_lines(text: str) -> list[str]:
    return [l for l in text.splitlines() if not l.strip().startswith("#")]

def _has_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


# ── OS-SYM1: bare package manager call in Python ─────────────────────────────

_BARE_PM_PY = [
    r"[\"']apt-get\s+install\b",
    r"[\"']apt\s+install\b",
    r"[\"']dpkg\s+-i\b",
    r"[\"']pacman\s+-S\b",
]

_PM_GUARDS_PY = [
    r"_detect_pkg_manager\(",
    r"detect_pkg_manager\(",
    r"\bpm_install\b",
]

def _detect_os_sym1_py(ctx: AuditContext) -> DetectorResult:
    samples: list[str] = []
    for f in _py_files(ctx.repo_root):
        text = _file_text(f)
        lines = _non_comment_lines(text)
        joined = "\n".join(lines)
        if not _has_pattern(joined, _BARE_PM_PY):
            continue
        if _has_pattern(joined, _PM_GUARDS_PY):
            continue
        rel = str(f.relative_to(ctx.repo_root))
        for i, line in enumerate(lines, 1):
            for pat in _BARE_PM_PY:
                if re.search(pat, line):
                    samples.append(f"{rel}:{i}: bare `{line.strip()}` — use _detect_pkg_manager() guard")
                    break
    return DetectorResult(count=len(samples), samples=samples[:10])


# ── OS-SYM1S: bare package manager call in shell ─────────────────────────────

_BARE_PM_SH = [
    r"\bapt-get\s+install\b",
    r"\bapt\s+install\b",
    r"\bdpkg\s+-i\b",
    r"\bpacman\s+-S\b",
]

_PM_GUARDS_SH = [
    r"command\s+-v\s+(apt|pacman|brew|dpkg)",
    r"which\s+(apt|pacman|brew|dpkg)",
    r"\bdetect_pm\b",
    r"\bpm_install\b",
]

def _detect_os_sym1_sh(ctx: AuditContext) -> DetectorResult:
    samples: list[str] = []
    for f in _sh_files(ctx.repo_root):
        text = _file_text(f)
        lines = _non_comment_lines(text)
        joined = "\n".join(lines)
        if not _has_pattern(joined, _BARE_PM_SH):
            continue
        if _has_pattern(joined, _PM_GUARDS_SH):
            continue
        rel = str(f.relative_to(ctx.repo_root))
        for i, line in enumerate(lines, 1):
            for pat in _BARE_PM_SH:
                if re.search(pat, line):
                    samples.append(f"{rel}:{i}: bare `{line.strip()}` — add detect_pm() guard")
                    break
    return DetectorResult(count=len(samples), samples=samples[:10])


# ── entry point ───────────────────────────────────────────────────────────────

def build_oc_detectors() -> list[Detector]:
    return [
        Detector("OS-SYM1",  "bare package manager call in Python without detection guard", "open", _detect_os_sym1_py, HIGH),
        Detector("OS-SYM1S", "bare package manager call in shell without detection guard",  "open", _detect_os_sym1_sh, HIGH),
    ]
