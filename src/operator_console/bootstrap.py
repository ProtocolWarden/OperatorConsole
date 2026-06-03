# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""Generate Claude context from repo-local .console/ state files."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Ordered sections in the context — label maps to filename
CONTEXT_SECTIONS = [
    ("task.md",   "Task"),
    ("guidelines.md",    "Guidelines"),
    ("backlog.md",    "Backlog"),
    ("log.md",   "Log"),
]

# Hot-trim (tiered-memory spec §5): the log grows without bound, so compiling it
# whole bloats the always-loaded startup blob (seen at 3k–6k lines in active
# repos). Compile only the most-recent entries here; the full history stays in
# the source `.console/log.md` (read on demand). Entries are appended newest-last
# across the fleet, so the tail is the recent set. Tunable via env.
LOG_RECENT_ENTRIES = int(os.environ.get("CONSOLE_LOG_RECENT_ENTRIES", "5") or "5")


def _trim_log(content: str, max_entries: int = LOG_RECENT_ENTRIES) -> str:
    """Keep the log preamble + the most-recent ``max_entries`` ``## `` entries,
    replacing older ones with a one-line pointer to the full source file.

    Newest-last convention (the fleet appends to the bottom), so the tail is the
    recent set. A non-positive ``max_entries`` keeps everything (disables trim).
    Returns ``content`` unchanged when it has no recognizable entries.
    """
    if max_entries <= 0:
        return content
    parts = re.split(r"(?m)^(?=## )", content)
    if len(parts) <= 1:
        return content
    preamble, entries = parts[0], parts[1:]
    if len(entries) <= max_entries:
        return content
    omitted = len(entries) - max_entries
    note = (
        f"_{omitted} older entr{'y' if omitted == 1 else 'ies'} omitted to keep "
        f"startup context lean — full history in `.console/log.md`._\n\n"
    )
    return preamble.rstrip() + "\n\n" + note + "".join(entries[-max_entries:]).strip() + "\n"


# Backlog sections that are historical/completed by name — dropped from the
# compiled blob (kept in source). Conservative: only unambiguously-historical
# headings. Active work (In Progress, Up Next, and any unrecognized section) is
# always kept. Matched case-insensitively against the `## ` heading text.
_HISTORICAL_BACKLOG_HEADING = re.compile(
    r"^##\s+(done\b|recently completed|previously in progress|archived?\b|"
    r"cycle\b.*\bupdates?\b)",
    re.IGNORECASE,
)


def _trim_backlog(content: str) -> str:
    """Drop unambiguously-historical/completed sections from the compiled backlog
    (spec §5: completed inventory and per-cycle history are not needed in every
    session's startup context). Active sections (In Progress, Up Next, and any
    unrecognized heading) are kept whole; the source ``.console/backlog.md``
    retains everything. Returns ``content`` unchanged when nothing matches.
    """
    parts = re.split(r"(?m)^(?=## )", content)
    if len(parts) <= 1:
        return content
    kept: list[str] = []
    dropped = 0
    for part in parts:
        heading = part.splitlines()[0] if part.strip().startswith("## ") else ""
        if heading and _HISTORICAL_BACKLOG_HEADING.match(heading.strip()):
            dropped += 1
            continue
        kept.append(part)
    if not dropped:
        return content
    note = (
        f"\n_{dropped} historical/completed backlog section(s) omitted to keep "
        f"startup context lean — see `.console/backlog.md`._\n"
    )
    return "".join(kept).rstrip() + "\n" + note

# Files pulled from peer repos (guidelines are repo-specific, skip them)
PEER_FILES = [
    ("task.md", "Task"),
    ("backlog.md",  "Backlog"),
]


def _get_branch(repo_root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def build_resume_prompt(
    repo_root: Path,
    files: list[str] | None = None,
    peer_roots: list[tuple[str, Path]] | None = None,
    profile_name: str | None = None,
) -> str:
    console_dir = repo_root / ".console"
    sections: list[str] = []

    if files:
        files_to_read = [(Path(f).name, Path(f).name.replace(".md", "").replace("-", " ").title())
                         for f in files]
    else:
        files_to_read = list(CONTEXT_SECTIONS)

    for filename, label in files_to_read:
        path = console_dir / filename
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if filename == "log.md":
                content = _trim_log(content).strip()
            elif filename == "backlog.md":
                content = _trim_backlog(content).strip()
            if content:
                sections.append(f"## {label}\n\n{content}")

    if peer_roots:
        for peer_name, peer_root in peer_roots:
            peer_console = peer_root / ".console"
            for filename, label in PEER_FILES:
                path = peer_console / filename
                if path.exists():
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        sections.append(f"## Peer: {peer_name} — {label}\n\n{content}")

    if not sections:
        return (
            "No .console/ context files found.\n"
            "Run: console init  to initialize context files for this repo."
        )

    repo_root = repo_root.resolve()
    branch = _get_branch(repo_root)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    profile_str = f" · Profile: {profile_name}" if profile_name else ""

    runtime = (
        f"## Runtime Context\n\n"
        f"- **Repo**: {repo_root.name}\n"
        f"- **Repo root**: `{repo_root}`\n"
        f"- **Branch**: `{branch}`\n"
        f"- **Generated**: {timestamp}{profile_str}\n"
    )
    sections.append(runtime)

    header = (
        f"# OperatorConsole Context — {repo_root.name}\n\n"
        f"_Generated {timestamp} · Branch: {branch}{profile_str}_\n\n"
        "This is your compiled startup context. Read it before acting.\n"
        "The source files in `.console/` are the editable truth — this file is generated.\n\n"
        "---\n\n"
    )
    return header + "\n\n---\n\n".join(sections)


def write_bootstrap_file(
    repo_root: Path,
    files: list[str] | None = None,
    peer_roots: list[tuple[str, Path]] | None = None,
    profile_name: str | None = None,
) -> Path:
    prompt = build_resume_prompt(repo_root, files, peer_roots, profile_name)
    out = repo_root / ".console" / ".context"
    out.write_text(prompt, encoding="utf-8")
    return out


# ── ContextLifecycle anchoring ────────────────────────────────────────────────
# Console-launched CLIs anchor at their owning manifest via `cl session start`.
# CL_HOME is machine state (the local CL clone path) so it can't live in a repo,
# and zellij panes are non-interactive non-login shells that source neither
# ~/.bashrc nor ~/.claude/settings.json. So we resolve `cl` once here — in the
# console process, which inherits CL_HOME from its launching shell — and bake the
# literal path into every generated wrapper rather than re-resolving in the pane.


def _resolve_cl_bin() -> str:
    """Absolute path to the ContextLifecycle `cl` binary, or "" if unavailable.

    Order: CL_HOME env → ~/.claude/settings.json env.CL_HOME → `cl` on PATH.
    """
    cl_home = os.environ.get("CL_HOME", "")
    if not cl_home:
        try:
            settings = Path.home() / ".claude" / "settings.json"
            if settings.exists():
                data = json.loads(settings.read_text(encoding="utf-8"))
                cl_home = data.get("env", {}).get("CL_HOME", "")
        except Exception:
            cl_home = ""
    if cl_home:
        candidate = Path(cl_home) / "bin" / "cl"
        if candidate.exists():
            return str(candidate)
    return shutil.which("cl") or ""


def _cl_anchor_prelude() -> str:
    """Bash prelude that anchors the session via `cl session start`.

    The `cl` path is resolved and baked in at generation time. If `cl` can't be
    found, the session launches unanchored and the prelude is an inert comment.
    """
    cl_bin = _resolve_cl_bin()
    if not cl_bin:
        return "# ContextLifecycle: cl not found at launch — session unanchored.\n"
    safe = cl_bin.replace("'", "'\\''")
    return (
        "# ContextLifecycle: anchor at owning manifest (cl path baked at launch).\n"
        f"_CL_BIN='{safe}'\n"
        'eval "$("$_CL_BIN" session start 2>/dev/null || true)"\n'
    )


def get_claude_command(
    profile: dict,
    repo_root: Path,
    console_dir: Path | None = None,
    session_key: str | None = None,
    claude_cwd: Path | None = None,
) -> str:
    """Return a shell command string that launches Claude with session resume support.

    Generates a wrapper script in /tmp that:
      1. Reads the saved session ID (config/profiles/<key>.session)
      2. Runs `claude --resume <id>` or fresh Claude if none saved
      3. After exit, saves the newest session ID for this project
    """
    import tempfile

    if console_dir is None:
        return "claude"

    key = (session_key or profile.get("name", "unknown")).lower()
    cwd = claude_cwd or repo_root

    session_file = console_dir / "config" / "profiles" / f"{key}.session"

    # Derive the Claude project dir from the cwd (mirrors Claude's own convention)
    project_key = str(cwd.resolve()).lstrip("/").replace("/", "-")
    project_dir = Path.home() / ".claude" / "projects" / f"-{project_key}"

    sf = str(session_file).replace("'", "'\\''")
    pd = str(project_dir).replace("'", "'\\''")

    # RC file: sourced by the post-claude interactive shell so that typing
    # `claude` re-anchors automatically. The `cl` path is baked at launch.
    cl_bin = _resolve_cl_bin()
    safe_cl = cl_bin.replace("'", "'\\''")
    rc_path = Path(tempfile.gettempdir()) / f"console-rc-{key}.sh"
    rc_path.write_text(
        "[ -f ~/.bashrc ] && source ~/.bashrc\n"
        "claude() {\n"
        f"    local _cl='{safe_cl}'\n"
        '    [ -n "$_cl" ] && [ -x "$_cl" ] && eval "$("$_cl" session start 2>/dev/null || true)"\n'
        '    command claude "$@"\n'
        "}\n",
        encoding="utf-8",
    )
    rc_path.chmod(0o755)
    src = str(rc_path).replace("'", "'\\''")

    script = (
        "#!/usr/bin/env bash\n"
        + _cl_anchor_prelude()
        + f"SESSION_FILE='{sf}'\n"
        f"PROJECT_DIR='{pd}'\n"
        "_save_session() {\n"
        "    newest=$(ls -t \"$PROJECT_DIR\"/*.jsonl 2>/dev/null | head -1)\n"
        "    [ -n \"$newest\" ] && basename \"$newest\" .jsonl > \"$SESSION_FILE\" || true\n"
        "}\n"
        "_save_session\n"
        "if [ -f \"$SESSION_FILE\" ]; then\n"
        "    claude --resume \"$(cat \"$SESSION_FILE\")\" || claude\n"
        "else\n"
        "    claude\n"
        "fi\n"
        "_save_session\n"
        # Drop to an interactive shell where `claude` re-anchors automatically.
        f"exec bash --rcfile '{src}' -i\n"
    )

    script_path = Path(tempfile.gettempdir()) / f"console-claude-{key}.sh"
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o755)

    safe_path = str(script_path).replace("'", "'\\''")
    return f"bash '{safe_path}'"


def get_codex_command(
    profile: dict,
    repo_root: Path,
    console_dir: Path | None = None,
    session_key: str | None = None,
) -> str:
    """Return a shell command string that launches Codex CLI, or a usable shell if not installed.

    Single-repo (session_key is None): uses `codex resume --last` so codex's own cwd
    filter picks the right session — avoids cross-profile UUID contamination.

    Multi-repo (session_key provided): file-based UUID keyed by tab name, because all
    profiles share the same cwd (~/Documents/GitHub) and codex can't distinguish them.
    """
    import tempfile

    codex_cfg    = profile.get("codex", {})
    codex_bin    = codex_cfg.get("bin", "codex")
    safe_bin     = codex_bin.replace("'", "'\\''")
    # Default to full local access for Console-launched Codex sessions:
    # no per-command approval prompts and no filesystem sandbox. Override
    # per-profile with codex.approval_mode: "" or codex.sandbox_mode: "" to
    # get Codex defaults instead.
    approval     = codex_cfg.get("approval_mode", "-a never")
    approval_arg = f" {approval}" if approval else ""
    sandbox      = codex_cfg.get("sandbox_mode", codex_cfg.get("sandbox", "-s danger-full-access"))
    sandbox_arg  = f" {sandbox}" if sandbox else ""
    codex_args   = f"{approval_arg}{sandbox_arg}"

    not_found_block = (
        "#!/usr/bin/env bash\n"
        + _cl_anchor_prelude()
        + f"if ! command -v '{safe_bin}' &>/dev/null; then\n"
        "  echo 'codex CLI not found.'\n"
        "  echo 'Install: npm install -g @openai/codex'\n"
        "  exec bash -l\n"
        "fi\n"
    )

    if session_key is None:
        # Single-repo: let codex filter by cwd natively
        script = (
            not_found_block
            + f"'{safe_bin}'{codex_args} resume --last 2>/dev/null || '{safe_bin}'{codex_args}\n"
            + "exec bash -l\n"
        )
        key = profile.get("name", "unknown").lower()
    else:
        # Multi-repo: file-based UUID keyed by tab name
        key = session_key.lower()
        if console_dir is not None:
            session_file = console_dir / "config" / "profiles" / f"{key}.codex-session"
            sf = str(session_file).replace("'", "'\\''")
            _codex_save = (
                "newest=$(find ~/.codex/sessions -name 'rollout-*.jsonl' 2>/dev/null"
                + " | sort -r | head -1)\n"
                + "[ -n \"$newest\" ] && basename \"$newest\" .jsonl"
                + " | grep -oE '[0-9a-f-]{36}$' > \"$SESSION_FILE\" || true\n"
            )
            script = (
                not_found_block
                + f"SESSION_FILE='{sf}'\n"
                # Refresh session file at launch — catches missed saves from abrupt shutdown
                + _codex_save
                + "if [ -f \"$SESSION_FILE\" ]; then\n"
                + f"    '{safe_bin}'{codex_args} resume \"$(cat \"$SESSION_FILE\")\" || '{safe_bin}'{codex_args}\n"
                + "else\n"
                + f"    '{safe_bin}'{codex_args}\n"
                + "fi\n"
                # Save again after clean exit
                + _codex_save
                + "exec bash -l\n"
            )
        else:
            script = (
                not_found_block
                + f"'{safe_bin}'{codex_args}\n"
                + "exec bash -l\n"
            )

    script_path = Path(tempfile.gettempdir()) / f"console-codex-{key}.sh"
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o755)

    safe_path = str(script_path).replace("'", "'\\''")
    return f"bash '{safe_path}'"


def get_aider_command(
    profile: dict,
    repo_root: Path,
    console_dir: Path | None = None,
    session_key: str | None = None,
) -> str:
    """Return a shell command string that launches aider, or a usable shell if not installed.

    Reads aider config from profile.get("aider", {}):
      - bin: binary name (default "aider")
      - model: model name (default None — uses aider's own default)
      - auto_commits: bool (default True; False adds --no-auto-commits)
    """
    import tempfile

    aider_cfg    = profile.get("aider", {})
    aider_bin    = aider_cfg.get("bin", "aider")
    safe_bin     = aider_bin.replace("'", "'\\''")
    model        = aider_cfg.get("model", None)
    auto_commits = aider_cfg.get("auto_commits", True)

    safe_repo = str(repo_root).replace("'", "'\\''")

    not_found_block = (
        "#!/usr/bin/env bash\n"
        + _cl_anchor_prelude()
        + f"if ! command -v '{safe_bin}' &>/dev/null; then\n"
        "  echo 'aider not found.'\n"
        "  echo 'Install: pip install aider-chat'\n"
        "  exec bash -l\n"
        "fi\n"
    )

    # Build aider argument list
    extra_args = ""
    if model:
        safe_model = model.replace("'", "'\\''")
        extra_args += f" '--model={safe_model}'"
    if not auto_commits:
        extra_args += " '--no-auto-commits'"

    key = (session_key or profile.get("name", "unknown")).lower()

    script = (
        not_found_block
        + f"cd '{safe_repo}'\n"
        + f"'{safe_bin}'{extra_args}\n"
        + "exec bash -l\n"
    )

    script_path = Path(tempfile.gettempdir()) / f"console-aider-{key}.sh"
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o755)

    safe_path = str(script_path).replace("'", "'\\''")
    return f"bash '{safe_path}'"


def ensure_claude_md(
    repo_root: Path,
    templates_dir: Path,
    extra_files: list[str] | None = None,
) -> None:
    claude_md = repo_root / "CLAUDE.md"
    marker      = "<!-- console-context -->"
    end_marker  = "<!-- /console-context -->"

    extra_lines = ""
    if extra_files:
        standard = {"guidelines.md", "task.md", "backlog.md", "log.md"}
        extras = [Path(f).name for f in extra_files if Path(f).name not in standard]
        if extras:
            extra_lines = "\nAdditional context files also compiled into the startup context:\n" + \
                "\n".join(f"- `.console/{name}`" for name in extras) + "\n"

    block = f"""{marker}
## OperatorConsole Context

At the start of each session, read the compiled context before acting:

- `.console/.context` — compiled startup context (generated fresh each launch)

The context file contains your current task, guidelines, backlog, log, and runtime context.
{extra_lines}
**Source files** (editable truth — update these, not the context file):

| File | Role |
|------|------|
| `.console/task.md` | Current objective and definition of done |
| `.console/guidelines.md` | Repo policy, branch rules, operating constraints |
| `.console/backlog.md` | Work inventory — in-progress, up-next, done |
| `.console/log.md` | Recent decisions, stop points, what changed and why |

After meaningful progress, update `.console/backlog.md` and `.console/log.md`.
Do not edit `.console/.context` directly — it is regenerated at each launch.
{end_marker}"""
    if claude_md.exists():
        import re
        existing = claude_md.read_text(encoding="utf-8")
        if marker in existing and end_marker in existing:
            # Replace only the fenced managed block; preserve content outside it
            new_text = re.sub(
                r"<!-- console-context -->.*?<!-- /console-context -->",
                block,
                existing,
                flags=re.DOTALL,
            )
            claude_md.write_text(new_text.rstrip() + "\n", encoding="utf-8")
        elif marker in existing:
            # Old format without closing fence — replace to end of file, append tail if any
            new_text = re.sub(
                r"<!-- console-context -->.*",
                block,
                existing,
                flags=re.DOTALL,
            )
            claude_md.write_text(new_text.rstrip() + "\n", encoding="utf-8")
        elif "## OperatorConsole Context" in existing:
            # Old format without marker — replace from that heading onward
            new_text = re.sub(
                r"## OperatorConsole Context.*",
                block,
                existing,
                flags=re.DOTALL,
            )
            claude_md.write_text(new_text.rstrip() + "\n", encoding="utf-8")
        else:
            claude_md.write_text(existing.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
    else:
        claude_md.write_text(block + "\n", encoding="utf-8")


# ── CLI update helpers ────────────────────────────────────────────────────────


_CLI_UPDATES: list[tuple[str, list[str]]] = [
    ("claude",  ["claude", "update"]),
    ("codex",   ["npm", "install", "-g", "@openai/codex"]),
    ("aider",   ["pipx", "upgrade", "aider-chat"]),
]


_UPDATE_LOG = Path("/tmp/console-cli-update.log")


def spawn_update_clis_background() -> None:
    """Fire-and-forget background CLI update; output goes to /tmp/console-cli-update.log."""
    import sys
    log = _UPDATE_LOG.open("w")
    try:
        subprocess.Popen(
            [sys.executable, "-c",
             "from operator_console.bootstrap import update_clis; r = update_clis(); "
             "[print(f'{k}: {v}') for k,v in r.items()]"],
            stdout=log, stderr=log,
            start_new_session=True,
        )
    except Exception:
        pass


def update_clis(*, verbose: bool = False) -> dict[str, str]:
    """Run update commands for claude, codex, and aider. Returns {name: status}."""
    results: dict[str, str] = {}
    for name, cmd in _CLI_UPDATES:
        bin_name = cmd[0]
        if not shutil.which(bin_name):
            results[name] = "skipped (not found)"
            continue
        try:
            r = subprocess.run(cmd, capture_output=not verbose, text=True, timeout=120)
            results[name] = "ok" if r.returncode == 0 else f"failed (exit {r.returncode})"
        except subprocess.TimeoutExpired:
            results[name] = "timeout"
        except Exception as exc:
            results[name] = f"error: {exc}"
    return results

