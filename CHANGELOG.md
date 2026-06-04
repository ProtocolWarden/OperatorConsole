# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- 2026-06-04: reconciled `console-symlink` — Restore cmd_install as `console symlink` (was dead code) (history archived).
- 2026-06-04: reconciled `aider-launcher` — Implement get_aider_command (launcher with profile/bin/model/auto_commits) (history archived).
- 2026-06-04: reconciled `spawn-update-clis-background` — Restore spawn_update_clis_background with _UPDATE_LOG constant (history archived).
- 2026-06-04: reconciled `read-decision-run-summary` — Wire read_decision into run_summary (decision_basis, decision_confidence) (history archived).
- 2026-06-04: reconciled `backend-missing-exit` — any_backend_missing gates run_providers exit code (history archived).
- 2026-06-04: reconciled `cxrp-execution-result` — CxrpExecutionResult fully implemented (parse + summarize) (history archived).
- 2026-06-04: reconciled `status-pane` — Curses status pane — collapsible sections, scroll, backend caps, resource gate, banners (history archived).
- 2026-06-04: reconciled `cl-anchoring` — ContextLifecycle anchoring — resolve cl once, bake path, re-anchor pane shells (history archived).
- 2026-06-04: reconciled `contextguard-hooks` — Wire ContextGuard / cl hooks into OperatorConsole's own .claude/ (history archived).
- 2026-06-04: reconciled `phase4-hot-trim` — Phase 4 hot-trim — compile only recent log entries + active backlog into context blob (history archived).
- 2026-06-04: reconciled `platform-profiles` — Platform-group profile expansion + git_watcher group wiring (RepoGraph, ProtocolWarden, executors, CL) (history archived).
