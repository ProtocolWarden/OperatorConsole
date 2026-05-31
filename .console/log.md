# Log

## 2026-05-30 — status pane: per-model worker backend rows + split Backend Limits

"Backend Limits → Worker Backends" showed only the subsection header on height squeeze: the single backend_caps section nested two sub-headers under its own title, and the virtual buffer keeps only a section's first sec_h lines on overflow, so the data rows fell off. Split into two flat sections (worker_backends, executor_lanes) so each keeps header + data independently. Also rendered claude_code per model (sonnet/opus/haiku) reading the controller's new backend_limit_kinds: a model_weekly limit marks only that model, session_5h/global_weekly mark all. Added a "… +N more" indicator when a section is truncated. 27 pane tests pass; custodian OK.

## 2026-05-28 — Wire ContextGuard hooks into OperatorConsole

OC previously carried no `.claude/` hooks, so developing OC itself ran without
anchor enforcement. Added the committed executor-shim pair
(`.claude/hooks/pre_tool_use.sh` + `stop.sh`) and `.claude/settings.json`,
mirroring TeamExecutor/CritiqueExecutor exactly — the shim delegates to
`cl hook ...`. OC resolves its anchor to PlatformManifest via RepoGraph
(verified). PlatformManifest's provision-machine.sh now lists OperatorConsole in
COMMITTED_HOOK_REPOS so the hook-health check verifies it.

## 2026-05-27 — Redesign CL anchoring: resolve cl once, bake the path

Replaced the runtime resolution dance (repeated in 3 wrapper builders + the rc
file) with a single Python resolver, `_resolve_cl_bin()`, and a
`_cl_anchor_prelude()` that bakes the resolved absolute `cl` path into each
generated wrapper.

Why: `cl` lives at `$CL_HOME/bin/cl`, and CL_HOME is *machine state* (the local
clone path), so it can't live in a repo. Zellij panes are non-interactive,
non-login shells that source neither `~/.bashrc` nor `~/.claude/settings.json`,
so resolving `cl` *inside the pane* was unreliable (the earlier `source
~/.bashrc` and inline-python-reading-settings.json hacks). The `console` process
itself *does* inherit CL_HOME from the interactive shell that launched it — so
we resolve there, once, and bake the literal path in. Resolution order:
CL_HOME env → settings.json env.CL_HOME → `cl` on PATH. If none resolve, the
prelude is an inert comment (session launches unanchored, never errors).

Verified with `env -i` (clean env, no CL_HOME — mimics a pane): baked path
anchors CL_ANCHOR correctly where `source ~/.bashrc` produced nothing.

Custodian follow-up: documented CL_HOME in `.env.example` (E1) and trimmed the
comment + a redundant local import to keep bootstrap.py under the 500-line cap
(C29).

## 2026-05-27 — Wire provision-machine.sh into setup.sh

setup.sh now calls PlatformManifest/scripts/provision-machine.sh after the local bootstrap. Passes through --with-private and --force-hooks flags; --skip-provision keeps the old local-only behavior.

## 2026-05-26 — Repair pre-existing watcher_pane tests

Fixed 9 stale/regressed failures in tests/test_watcher_pane.py.

- Banner-message tests (healthy/switchboard/gate/queue/info): STALE tests. The
  banner copy was intentionally title-cased and reworded ("All Systems Nominal",
  "SwitchBoard Offline", "Global Gate at Cap", "Queue Depth", "Stabilizing").
  Updated assertions to the current strings.
- test_exec_budget_reads_usage: STALE test — it never isolated _resource_gate(),
  which reads the real on-disk OC config; gate values shadow the env caps the
  test sets, so daily_cap came back as the config's value. Added a monkeypatch
  stubbing _resource_gate -> {} so the env-override path is the one exercised.
- test_critical_sorts_before_warning_sorts_before_info: STALE premise — the
  "just started" INFO banner is intentionally PINNED to the front of the cycle,
  so a linear crit<warn<info ordering can't hold within 30s of launch. Split
  into test_critical_sorts_before_warning (pure severity order, started_at=0)
  and test_just_started_info_is_pinned_to_front (documents the pinning).
- test_overflow_proportional / test_collapsed_during_overflow: REAL code bug.
  _allocate_section_rows did no overflow scaling and over-allocated far past the
  available rows (42/31 vs cap 10). Added proportional down-scaling on overflow
  with a min(3, natural) floor; natural-fit, size_mult, collapsed, and empty
  paths preserved.

tests/test_watcher_pane.py: 27 passed. Full suite: 132 passed, 3 failed —
the 3 are pre-existing cxrp schema_version 0.2-vs-0.3 mismatches in
tests/test_cxrp_capture.py, unrelated to this change. Custodian clean.

## 2026-05-22 — Rename ContextLifecycleProtocol → ContextLifecycle

Hard cutover. Renamed profile file from `contextlifecycleprotocol.yaml` to `contextlifecycle.yaml`. Updated all references in config, git_watcher, and platform.yaml.

## 2026-05-21 — Fix console-context block overwriting repo-owned CLAUDE.md content

bootstrap.py rewrote CLAUDE.md from the open marker to EOF (DOTALL), nuking anything below
the OC block. Fix: add <!-- /console-context --> closing fence; regex now replaces only the
fenced region. All existing CLAUDE.md files migrated to add the closing fence.

## 2026-05-21 — Add ContextLifecycle to platform group and git watcher

Added contextlifecycle to platform.yaml group list.
Added "Cognition" group to git_watcher.py _GROUPS (between Executors and Contracts)
containing ContextLifecycle. Profile yaml was already on main.

## 2026-05-19 — Update corerunner.yaml repo_root to CoreRunner/

Local directory renamed ExecutorRuntime/ → CoreRunner/. Updated profile path and GitHub repo remote URL.

## 2026-05-19 — ADR 0006 Phase 5: rename ExecutorRuntime → CoreRunner in OperatorConsole

- config/profiles/executorruntime.yaml → corerunner.yaml; name: CoreRunner.
- config/profiles/platform.yaml: executorruntime → corerunner group entry.
- src/operator_console/git_watcher.py: "ExecutorRuntime" → "CoreRunner" in Executors frozenset.
- repo_root path in corerunner.yaml intentionally still points to ExecutorRuntime/ dir — will update after Phase 6 GitHub rename.
- 121 of 129 tests pass; 8 pre-existing watcher_pane failures unrelated to this change.

## 2026-05-19 — Suppressed pre-existing C29/D11 custodian findings (git_watcher.py)

Added C29 suppression for git_watcher.py (518 lines, same rationale as other TUI
panel modules). Added D11 suppression for _put() helper duplicated between
git_watcher.py and watcher_status_pane.py (intentional micro-helper duplication).

## 2026-05-19 — Removed live kodo/archon references from src

Updated watcher_status_pane.py docstring (kodo → executor campaigns). Updated
demo.py YAML example (kodo: section → team_executor:, binary: kodo → team-executor).
Updated providers.py backend entry (kodo → team_executor with TeamExecutor install URL).

## 2026-05-13 — WorkStation → PlatformDeployment hard cutover

- Updated `README.md` and `docs/history/` to replace all `WorkStation`/`workstation` references with `PlatformDeployment`/`platformdeployment`.

## 2026-05-12 — Expand platform profile to RepoGraph and ProtocolWarden docs

Added `RepoGraph` and `ProtocolWarden.github.io` to the tracked `platform`
profile so the platform watcher and lazygit multi-repo view include both repos
by default. Aligned the profile docs and demo wording to the new platform set.

## 2026-05-12 — Remove WorkStation profile fallback

Updated the platform group to target `PlatformDeployment` directly, removed the
tracked `workstation.yaml` profile, and removed `WorkStation` fallback lookup
from the providers/demo/workers paths so the interactive git watcher and
platform commands resolve the deployment repo by its canonical name only.

## 2026-05-10 — Codex startup defaults to full access

Updated OperatorConsole's Codex launcher to start Codex panes with
`-a never -s danger-full-access` by default, matching the full-access operator
session profile. Profiles can still opt out with `codex.approval_mode: ""` or
`codex.sandbox_mode: ""`. Added startup tests for the default and opt-out paths.

## 2026-05-08 — Add .env.example

OperatorConsole reads 7 env vars (CONSOLE_PROFILE, PORT_SWITCHBOARD,
OPERATIONS_CENTER_*, ZELLIJ, ZELLIJ_SESSION_NAME) but had no documented
reference. Added .env.example with all vars commented out and explained.

_Chronological continuity log. Decisions, stop points, what changed and why._
_Not a task tracker — that's backlog.md. Keep entries concise and dated._

- 2026-05-12 — RepoGraph boundary artifact wiring tightened to file-only: the
  custodian audit path now materializes `REPOGRAPH_BOUNDARY_ARTIFACT_FILE` from a
  source locator before invoking Custodian, and the remaining deployment-facing
  templates were aligned to `PlatformDeployment` naming.

- Wire queue plumbing contract (2026-05-08, on chore/queue-plumbing-contract): Added `audit.plumbing` to `.custodian/config.yaml` for the queue artifact (OperatorConsole writes `~/.console/queue/<uuid>.json`, OC intake reads it). P1/P2/P3 all 0 findings live.

- Wire cross_repo config (2026-05-08, on chore/wire-cross-repo-config): Added `audit.cross_repo.platform_manifest_repo: ../PlatformManifest` to `.custodian/config.yaml`. Enables X1/X2/X3 detectors; live run shows 0 findings.

- codex --full-auto → -a never (2026-05-08, on fix/codex-full-auto): codex dropped --full-auto. Updated bootstrap.py default approval_mode to `-a never`; same fix applied to kodo sessions/codex.py, orchestrators/codex_cli.py, and benchmark/runner.py in that repo.

- Banner padding equalized and trimmed (2026-05-08, on fix/banner-equal-padding): Equalized lp and g to the same value, then trimmed 15% — both now `max(4, (w-1)*17//80)` (= (w-1)//4 × 0.85). At 120 cols: 25 spaces each side.

- Banner padding unified at half original (2026-05-08, on fix/banner-half-padding): Both single and multi-banner now use lp=(w-1)//4 and g=max(6,(w-1)//6) — half the original multi-banner values. Removes the single/multi branch entirely.

- Banner single-loop padding at half size (2026-05-08, on fix/banner-single-padding): Single-banner re-stream gets lp=(w-1)//4 and g=max(6,(w-1)//6) — half the original values — so there's a visible breath between loops. Multi-banner keeps lp="" and g="    " (4 spaces); the crossfade coloring is the boundary signal there.

- Banner padding stripped (2026-05-08, on fix/banner-strip-padding): Removed leading pad (`(w-1)//2` spaces) and large gap (`max(12, (w-1)//3)` spaces) from `_build_unit` and `_banner_unit_len`. Both cases now use a fixed 4-space separator between units — the tape streams the next banner in seamlessly so the large pads were dead space.

- Multi-banner cycling system + white-on-red fix (2026-05-08, on feat/multi-banner-cycle): The single-purpose stall banner becomes a 4-level banner system. CRITICAL (white on red — fixes the previous black-on-red look from A_REVERSE), WARNING (white on yellow), INFO (white on cyan), HEALTHY (white on green). Conditions: CRITICAL = stall / SwitchBoard offline / resource gate at cap or below RAM floor. WARNING = backend at concurrency cap / queue depth ≥ 10 / free RAM within 1.2× of gate floor. INFO = first 30s after launch (readings stabilizing). HEALTHY = nothing else. Worst-first sort; cycle index advances every 15 frames (3s at 200ms tick); marquee restarts when cycling. Counter shown on banner when count > 1 ([N/M]). Banner block always renders so layout stays stable; middle_top fixed at 7. 8 new tests in TestBannerConditions; 26 watcher tests passing.

- Banner + footer divider lines (2026-05-08, on feat/banner-and-footer-dividers): Two visual changes. Top: when stall banner is up, layout becomes divider/marquee/divider/blank/title (was marquee/blank/title/blank/divider) — the two dividers frame the alert as its own block. Bottom: footer block now divider/hints/divider going up from the bottom edge (was just hints), with the existing trailing blank from System Resources sitting above the upper divider. Flash floats above the upper divider when present. middle_top=5 with banner / 3 without; footer_h=4 with flash / 3 without.

- Gate readout counts RAM + swap; title→section spacer (2026-05-08, on `feat/gate-readout-ram-plus-swap-and-spacer`): The `Global gate` row in System Resources now sums free RAM + free swap when comparing to `min_available_memory_mb`, matching the OC `UsageStore.available_memory_mb()` change shipping in OC PR #115. Cell label updated to `mem≥XMB (Y free, ram+swap)` so operators see the unit. Also bumps `middle_top` by one row so the first section visually detaches from the title/separator above it (no banner: title row 0 → sep row 1 → blank row 2 → first section row 3; banner: marquee row 0 → blank row 1 → title row 2 → sep row 3 → blank row 4 → first section row 5).

- Watcher polish: streaming banner, blank spacers, status-colored headers (2026-05-08, on `feat/global-resource-gate-readout-and-collapsed-default`): Three follow-ups landed alongside the resource-gate work. **Streaming stall banner**: when one or more roles' heartbeats go stale, the banner now scrolls horizontally as a marquee — `banner_offset` advances 2 chars per frame and the pane drops its tick from 500ms → 200ms while the banner is up. A blank spacer row sits between the banner and the `Operations Center` title so they don't crowd. **System Resources spacers**: blank lines added at the top (between separator and title) and bottom of the bottom-anchored block so it visually detaches from neighboring content. **Status-colored section headers**: each section's header now reflects the section's worst state — `Execution budget` and `Backend caps` propagate the worst row's color (red ≥100% / yellow ≥80% / green); `Services` colors the header by the SwitchBoard up/down flag; `Queue` reflects backlog size (red ≥10, yellow ≥5, green otherwise).

- Global resource gate readout + collapsed-by-default sections (2026-05-08, on `feat/global-resource-gate-readout-and-collapsed-default`): Two changes to the curses status pane. **Resource gate**: new `_resource_gate()` collector reads `resource_gate:` block from `operations_center.local.yaml` (parses `max_concurrent` + `min_available_memory_mb` with the same lightweight indented-block parser used by `_backend_caps`). The System Resources block now renders a `Global gate` row showing `in_flight N/M` (sum of all-backend in-flight from `backend_usage`) and `ram≥XXMB (Y free)`; line goes red when concurrency is at cap or free RAM is below the floor, yellow at ≥80% concurrency, green when under. When neither field is set, renders `(unset) — config: resource_gate.* in OC local.yaml` so operators see the feature exists. **Initial collapsed state**: all 9 collapsible sections (roles, active, recent, board, campaigns, queue, budget, backend_caps, services) start collapsed; operators expand what they need via click-on-header or `c`. System Resources is bottom-anchored, not part of the collapsible set, so it stays visible. 3 new tests for the gate parser + 18 watcher tests passing; ruff clean.

- Add PlatformManifest to platform group + watcher (2026-05-08, on `feat/add-platform-manifest-to-platform-group`): Tenth public platform repo joins the workspace. New `config/profiles/platformmanifest.yaml` mirrors the rxp/sourceregistry shape (lazygit + bash panes, pytest -q + ruff helpers). `config/profiles/platform.yaml` group list grew from 9 → 10. `.gitignore` allowlist updated. The git-dirty watcher reads its repo set from the loaded profile group at launcher.py:132 so no code change required — adding to platform.yaml is sufficient. All 10 group members validate cleanly via `validate_profile`.


- `console status` → watcher; system_status.py removed (2026-05-08, on `feat/status-watcher-default`): The dense curses pane (watcher_status_pane.py) is now the canonical `console status`. `--repo` / `--all` keep the text repo-snapshot path; `--json` dumps the watcher's `_collect()` snapshot for scripted consumers; `--watcher` / `--watch` aliases and the `console watcher` subcommand removed (status IS the watcher). `system_status.py` deleted in full — its budget/backend-caps/usage/resources helpers were already duplicated inside the watcher with the same I/O paths. tests/test_system_status.py replaced by tests/test_watcher_pane.py (collectors + allocator + CLI route assertions). test_pipeline.py system_status block dropped. docs/architecture.md tree updated. **Bonus fix**: roles section's auto-scroll was overriding the offset when collapsed, hiding the "Workers" header — now skipped while collapsed.

- Watcher: keep header visible when collapsed (2026-05-08, on `fix/watcher-collapsed-header-visible`): Scroll indicators (▲/▼) were overwriting the single visible row of a collapsed section, hiding the section name. Skip the indicator overlay when `collapsed[id]` is true so the header — including the ▶ marker — stays readable.

- Status pane: backend caps + per-backend usage (2026-05-08, on `feat/status-backend-caps-and-runs`): `console status` now surfaces a **Backend caps** block between Execution budget and System resources. Reads per-backend caps from `config/operations_center.local.yaml::backend_caps` and walks `usage.json` events to compute live counters: `hourly` / `daily` (execution events tagged with `backend=`), `in_flight` (execution_started minus execution_finished). Per-backend RAM threshold displayed as `ram≥<threshold>MB (free MB)` colored red when current free is below the floor. Layout: `kodo  in_flight 0/1  ram≥6144MB (2834 free)` — compact one-liner per backend with same yellow/red ratios as the global budget rows. JSON output gains `backend_caps` + `backend_usage` top-level keys. 4 new tests (yaml read, usage aggregation, JSON shape, missing-file fallbacks). Console suite still green; ruff clean.


- Curses pane: execution budget + backend caps live readout (2026-05-08, on `feat/curses-pane-budget-and-backend-caps`): The dense curses pane loaded into the zellij layout (`watcher_status_pane.py`) gains two new blocks between Queue and Services. **Execution budget**: hourly/daily counts vs env-driven caps with the same yellow≥80%/red≥100% color logic as `console status`. **Backend caps**: per-backend one-liner showing `h=used/limit  d=used/limit  in_flight=N/M  ram≥XXMB`; line color goes to the worst cap state (rate, concurrency, or RAM-below-floor). Three new data collectors (`_exec_budget`, `_backend_caps`, `_backend_usage`) read the same files OC enforces against — `usage.json` events tagged `backend=` and the `backend_caps` block in `operations_center.local.yaml`. Lightweight indented-block YAML parser added (handles inline comments) so the pane stays bun-free even on a bare interpreter without PyYAML — matching the existing pattern for the `plane:` block. 6 new tests; full pane test suite 17 pass; ruff clean.


- Curses pane: collapse + keyboard resize (2026-05-08, on `feat/curses-pane-collapse-and-resize`): Followup on per-section scroll. Each section header now shows ▼/▶ collapse indicator and a focus marker; clicking a header (BUTTON1 on the header row) toggles `collapsed_sections[id]`, and `c` keys the same toggle for the focused section. Collapsed sections render a single header row regardless of overflow. `+`/`-` adjust `size_mult[focused]` by 0.25 within `[0.3, 3.0]`; `=` resets. Allocator extended to honor both: collapsed → 1 row; non-collapsed natural = `ceil(len(lines) * mult)`. `_draw_main` now returns `(section_rows, header_rows)` so the click handler can hit-test the header row precisely (only when the section's scroll offset is 0). 4 new tests (collapsed→1, collapsed-during-overflow, size_mult grows natural, baseline still passes). Pane suite 26 passing; ruff clean. Mouse-drag resize was deliberately ruled out — fragile under zellij + multi-terminal mouse modes.

- Curses pane: per-section scroll + mouse wheel + CLI launcher (2026-05-08, on `feat/curses-pane-launcher-and-mouse`): The dense curses pane (`watcher_status_pane.py`) now scrolls each section independently. **Refactor**: `_build_main_lines` → `_build_sections` returning `list[{id, lines, sel_local}]`. New `_allocate_section_rows` distributes the middle area: each section gets its natural height when the total fits, otherwise proportional with a 3-row floor. **Per-section state**: `section_offsets: dict[str, int]` replaces the global scroll; each section renders its own slice with ▲/▼ indicators when there's more content. **Mouse wheel**: `curses.mousemask(ALL_MOUSE_EVENTS | REPORT_MOUSE_POSITION)` enabled; BUTTON4=up, BUTTON5=down, 3 lines per tick, routed by mouse y → section under cursor. Wheel events also set `focused_section` so subsequent PgUp/PgDn target the same section. **CLI launcher**: `console watcher` subcommand + `console status --watcher` flag both forward argv (incl. `--profile`) to the pane. 4 new tests (allocator natural fit / overflow proportional / empty sections / zero-available; plus CLI shortcut presence). Pane suite 23 tests passing; ruff clean.
## Recent Decisions

- Status pane: execution budget + system resources (2026-05-08, on `feat/status-budget-resources`): Two new sections in `console status` after the Watchers block. **Execution budget** reads OC's `tools/report/operations_center/execution/usage.json` for hourly/daily exec counts and shows them against env-driven caps (`OPERATIONS_CENTER_MAX_EXEC_PER_HOUR`/`DAY`, defaults 10/50). Color yellow at >=80%, red at >=100%, green otherwise. **System resources** shows process count + RAM/swap from /proc. RAM colored against OC's kodo dispatch threshold (kodo.min_kodo_available_mb, 6144 MB default); when free RAM drops below this OC silently blocks new kodo dispatches, so surfacing it explains why the budget might appear unmet. JSON output gains `execution_budget` + `system` top-level keys. 6 new tests; full console suite green.

| Decision | Rationale | Date |
|----------|-----------|------|
| docs/architecture.md refresh | Module tree updated to actual src/operator_console/ contents (not the old src/console/ path with missing modules); pane diagram updated to current single/multi-repo Zellij stack layout (claude/codex/aider stack, watcher status pane); session-tracking section rewritten to cover all three tools (Claude, Codex, Aider) instead of only Claude. | 2026-05-07 |
| WS architecture refs updated after subgrouping | WorkStation moved its architecture/ docs into adapters/, routing/, contracts/, execution/, policy/, system/ subdirs. Inbound README links rewritten. | 2026-05-07 |
| docs reorganization | Moved docs/migration/fob-operator-flow-update.md and docs/audits/final_rename_refactor_verification_2.md into docs/history/. Removed empty migration/ and audits/ dirs. | 2026-05-07 |
| docs/README.md index added | Required by Custodian R6 (newly landed). Indexes daily-use guides, architecture, migration, and audit history. | 2026-05-07 |
| README ## What OperatorConsole Is Not section | Replaced inline "OperatorConsole is not a neutral bootstrap script..." sentence with a proper `## What OperatorConsole Is Not` H2 section listing the four explicit anti-scopes. Required by Custodian R4 README detector (newly landed). | 2026-05-06 |
| README workspace-layout diagrams corrected (round 2) | First pass still drew shell/status as horizontally split panes; they're actually a Zellij **stack** (overlapping, switchable). Redrew center and right columns with explicit stack notation so the diagram matches launcher.py and Zellij's actual rendering | 2026-05-06 |
| README workspace-layout diagrams corrected | Single-repo and multi-repo ASCII diagrams + descriptions described an older layout (status bottom-left, shell as center pane, logs on right; stacked lazygits in multi). Replaced with current: lazygit | claude/codex/aider | shell+status (single); git_watcher | claude/codex/aider | shell+status (multi). Source of truth: src/operator_console/launcher.py | 2026-05-06 |
| README ownership boundary: contracts attributed to CxRP/RxP | Section listed contracts under OperationsCenter; canonical cross-repo contracts now live in CxRP/RxP. Updated to map Dockerfiles→WS, routing→SB, adapters→OC, contracts→CxRP/RxP | 2026-05-06 |
| Add ExecutorRuntime, SourceRegistry, RxP to platform group | Three new repos joined the platform tab + git-dirty watcher; new profile yamls (bootstrap_files empty until repos grow .console/), `.gitignore` allowlist updated to track them | 2026-05-06 |
| C41 json.dumps ensure_ascii=False | 13 json.dumps calls across 9 files now include ensure_ascii=False | 2026-05-03 |
| Ruff style violations resolved | E701/E702/E741/F401 across clean.py, cli.py, delegate.py, observer.py, watcher_status_pane.py, git_watcher.py, commands.py, auto_once.py, tab_capture.py | 2026-05-03 |
| CLAUDE.md: simplify console update instruction | "Before each commit" → "After meaningful progress" | 2026-05-02 |
| cmd_install restored as `console symlink` | Was dead code (no CLI dispatch); added case "symlink" in cli.py; symlinks CONSOLE_DIR/console → ~/.local/bin/console | 2026-05-02 |
| get_aider_command implemented | Old version was a stub printing an error; now a real launcher (profile["aider"]: bin/model/auto_commits); aider pane added to layout alongside claude/codex | 2026-05-02 |
| spawn_update_clis_background restored | _UPDATE_LOG constant re-added; wired into console update --background; fire-and-forget subprocess.Popen | 2026-05-02 |
| read_decision wired into run_summary | Reads decision.json from run dir; run_summary now includes decision_basis and decision_confidence from OC's routing decision | 2026-05-02 |
| queue.remove wired into console queue cancel | Short-prefix resolution so cancel abc matches abcdef1234; delegates to queue.remove() | 2026-05-02 |
| check_branch gains force param; --force-branch flag | console open <profile> --force-branch suppresses protected-branch warning entirely; wired through cli → _run_open → launch → check_branch | 2026-05-02 |
| any_backend_missing gates run_providers exit code | providers.run_providers() now returns 1 when any backend is absent (unless --wait); was tracking the bool but not acting on it | 2026-05-02 |
| CxrpExecutionResult fully implemented | parse_execution_result(payload) validates + deserializes to typed CxrpExecutionResult; summarize_execution_result() takes typed object; T2 exclusion removed (tests now have real asserts) | 2026-05-02 |
| .console/ migrated to standard naming | active-mission/standing-orders/mission-log/objectives → task/guidelines/log/backlog | 2026-05-02 |

## Stop Points

- Wire Custodian B1 privacy block (2026-05-08, on `chore/wire-b1-privacy-block`): Added top-level `privacy:` block to `.custodian/config.yaml` listing `VideoFoundry` and `videofoundry` as banned literals. B1 reports zero leaks on the public surface — defaults exclude operator-private workspaces, history docs, and the config file itself, so the block is purely declarative for now and acts as a forward guard against future leaks.

- CI doctor: drop stale D7 exclude_paths (2026-05-06, on `main`): D7 (dead method param) was retired in Custodian's tool-first deprecation pass. `.custodian/config.yaml` still referenced D7 under exclude_paths, which `custodian-doctor --strict` flagged as an unknown detector. Removed the block.

- CI license header (2026-05-06, on `main`): Added missing SPDX header to `.vulture_whitelist.py`. Same fix pattern applied across other ProtocolWarden repos. CI license-header job now passes.

## Notes

_Free-form scratch space. Clear periodically._

- Fix title/divider/section spacing (2026-05-08, on `fix/title-divider-spacer-position`): The previous spacer landed *between* the divider and the first section, leaving the divider hugging the title. Operator wanted the divider hugging the first section instead, with the blank row between the title and the divider. Reordered: no banner → title (0) / blank (1) / divider (2) / section (3); banner → marquee (0) / blank (1) / title (2) / blank (3) / divider (4) / section (5).

- Global Gate row: shorten + capitalize (2026-05-08, on `fix/global-gate-line-fit-and-caps`): The gate readout was overflowing on narrower terminals. Compressed `in_flight` → `i-f`, dropped the `, ram+swap` annotation (the RAM and Swap rows above already explain free memory composition), and dropped the `config: resource_gate.* in OC local.yaml` hint from the (unset) form. Label switched from `Global gate` → `Global Gate`. New format: `Global Gate    i-f 0/6  mem≥12288MB (22000 free)` — fits comfortably in 80-col terminals.

- Stall alert covers all 8 workers (2026-05-08, on `fix/stall-alert-covers-all-roles`): The previous detector globbed `heartbeat_*.json` files and only flagged roles whose file existed but was old. A role that never started (no heartbeat file) or whose heartbeat got cleaned up was invisible. Rewrote to iterate the canonical `_ROLES` tuple: a role is stalled when (a) PID missing/dead, OR (b) no heartbeat file, OR (c) heartbeat older than 10min. Now every declared worker is evaluated each tick.

- DC2+DC4 fixes (2026-05-08, on `fix/dc-class-findings`): docs/pipeline.md cross-repo reference rewritten as a full GitHub URL link (was a backticked relative path the local file couldn't resolve, tripping DC2). README.md gains an Architecture H2 above Workspace Layout, and First Run renamed to Quick start to satisfy DC4's required-section pattern. DC count: 3 → 0.

- Banner restore title→sections spacer (2026-05-08, on `fix/banner-restore-title-sections-spacer`): The banner-divider PR #23 dropped the title→divider gap that the no-banner path keeps. Restored: banner case now ends with title (4) → blank (5) → divider (6), first section at row 7. Both code paths now read the same below the title.

## 2026-05-08 — Hint bar marquee on overflow (fix/hint-bar-marquee)

Hint bar at h-2 overflowed in narrow windows and got truncated. When wider than
window, it now scrolls in lockstep with the top banner (reuses banner_offset).
When it fits, renders static as before. No new state — same tick.


## 2026-05-08 — Multi-line collapsible hint bar (replaces marquee)

Replaced marquee-on-overflow with a wrapped multi-line hint bar that
defaults to collapsed (' ? hints (press ? to expand)'). Footer height
tracks the hint rows; flash sits one row above. Added '?' key handler.


## 2026-05-08 — M1: CHANGELOG.md stub (Keep-a-Changelog format)

Added a minimal CHANGELOG.md so M1 (and M5 format check) pass.

## 2026-05-08 — DC8: Move Quick start before Architecture in README

Reorder per canonical convention: What X is → What X is not → Quick
start → Architecture → ...


## 2026-05-08 — Custodian round: OConsole clean (39 → 0)

T6/T7 exclude_paths for src/operator_console/** (TUI exercised via CLI,
not name-imported in tests). T8 for test_architecture_demo.py (subprocess+curses).
common_words += git_watcher (subcommand name, not a Python symbol).


## 2026-05-08 — Title Case all status pane text

Banner messages, section headers, descriptors (running/queued/active/pending/etc),
hint chunks, action submenu, log view, and toggle indicators all Title Cased.
STOPPED / STALL ALERT remain ALL CAPS as severity emphasis.


## 2026-05-08 — CI regression guard

Added .github/workflows/custodian-audit.yml + .hooks/pre-push.
Both run `custodian-multi --fail-on-findings`. CI is the source of
truth; pre-push catches regressions before they hit GitHub.


## 2026-05-08 — CI fix: Direct URL pip install syntax


## 2026-05-08 — A_BOLD on ERR + YLW for dark-terminal readability

Plain red on dark background is nearly invisible on most terminals.
Bolding both ERR and YLW promotes them to the bright variants — readable
on dark + light alike.


## 2026-05-08 — Expand cryptic Backend Caps + Global Gate cell labels


## 2026-05-08 — Title-Case displayed values; rename Backend Caps → Backend Limits

New _tc() helper Title-Cases snake_case identifiers for display only —
data unchanged. Wired into worker rows, active tasks, recent activity,
board, queue, backend rows, action submenu, log view header.
'(no caps)' → '(No Limits)'. Action submenu items also Title-Cased.


## 2026-05-08 — Global Gate three-liner; Execution Budget → Global Rate (single-line); spacers + ≥ spacing


## 2026-05-08 — Reorder pane sections by operator timeline

Swapped board ↔ campaigns in section build order. Final timeline:
Workers / Active (Present) → Recent (Past) → Campaigns / Board / Queue
(Future) → Global Rate / Backend Limits (Capacity) → Services (Infra)
→ System Resources / Global Gate (bottom-anchored).


## 2026-05-08 — Bottom-anchored collapsible sections

Restructured the bottom of the pane: System Resources, Global Gate, and
Global Rate are now three independently collapsible sections, all bottom-
anchored. Default-open: System Resources only; Gate + Rate collapsed.

- Replaced flat _resources_lines() with _bottom_sections() → list[dict]
- Removed top-section 'budget' (Global Rate moved to bottom)
- Bottom render loop: spacer + divider, then each section header (and
  body if expanded), divider between sections
- Click-on-header / 'c' / mouse-wheel hit-testing all work uniformly


## 2026-05-08 — Fix Global Gate header DIM-when-healthy; expand load column headers

- Worst-cell tier ladder now picks RUN over DIM when at least one cell
  is RUN — gate header reads green when configured + healthy (not grey).
- '1m / 5m / 15m' → '1 Min / 5 Min / 15 Min' (clearer time windows).
- '(N cores)' → '(N Cores)' (title-case suffix).


## 2026-05-08 — Reorder bottom sections: Rate → Gate → Resources


## 2026-05-08 — Single divider directly under Services (drop spacer-then-divider)


## 2026-05-08 — Anchor inter-block divider to last top section


## 2026-05-08 — Restore leading divider on bottom block (above Global Rate)


## 2026-05-08 — Top block as virtual scroll buffer

When all top sections are uncollapsed and overflow the middle area,
the top block scrolls as a single virtual buffer (mouse-wheel + PgUp/
Dn). Bottom-anchored sections (Rate/Gate/Resources) stay put; the
top block flows behind them.

- _allocate_section_rows: drop proportional scaling, return natural sizes
- _draw_main: build vbuf from sections with dividers, render slice
  starting at top_scroll_offset, expose section_buf_ranges for hit-testing
- Mouse wheel anywhere over top sections scrolls top_scroll_offset
- PgUp/PgDn/Home/End now operate on top_scroll_offset
- Top block scroll arrows on boundary rows (▲/▼) when scrolled
- Dropped per-section scrolling for top sections (kept section_offsets
  signature for compatibility)


## 2026-05-08 — Drop top-block auto-scroll (operator-driven only)


## 2026-05-08 — Banner cycle buffer: leading pad + longer gap + 6s dwell


## 2026-05-08 — `x` collapse all + banner cycles after full scroll


## 2026-05-08 — Banner continuous-stream cycling (no hard cut)


## 2026-05-08 — Pin 'Just Started' banner to front of cycle (override severity sort)


- Status pane header layout (2026-05-09, on main): removed blank rows above and below "Operations Center" header (original rows 3 and 5); retained both separator lines; header now at row 3, blank breathing row at 4, sep at 5, content at 6. middle_top 7→6.

## 2026-05-10 — GitHub username migration

- Updated repo-owned references from the previous GitHub username to `ProtocolWarden` after the account rename.
- Scope: license headers, GitHub URLs, workflow install commands, manifests, dependency URLs, examples, and local owner defaults where present.

## 2026-05-13 — Add repograph/protocolwarden profiles; fix git_watcher columns

- Created `config/profiles/repograph.yaml` and `config/profiles/protocolwarden.github.io.yaml`; whitelisted both in `.gitignore`.
- `git_watcher.py`: name and branch column widths now computed dynamically from actual repo names so long entries like `ProtocolWarden.github.io` don't clobber adjacent columns.

## 2026-05-10 — Console setup and Custodian hook resolution

- Added non-interactive `setup.sh` to bootstrap OperatorConsole and symlink `console` into `~/.local/bin`.
- Updated the pre-push guard to prefer system `custodian-multi`, with repo venv and sibling Custodian venv fallbacks.

## 2026-05-13 — Add CLAUDE.md and .custodian/tmp*.yaml to .gitignore

- Added CLAUDE.md to .gitignore
- Added .custodian/tmp*.yaml to exclude custodian audit temp files

### ADR 0005 — Add executor repos to platform profile (2026-05-18)
Added teamexecutor, dagexecutor, critiqueexecutor, protocolwarden to platform group.
Created profile yamls for each with lazygit git pane and standard helpers.

## 2026-05-23 — Genericize fleet-repo ref + standardize hook

- Genericized SyncingSolution ref in .custodian/config.yaml comment (public repo; private fleet layer must not be named). Standardized .hooks/pre-push.

## 2026-05-24 — Platform tab anchors at PlatformManifest + export CL_ANCHOR

- launcher._multi_pane_block: cross-repo group tab cwd → PlatformManifest (was bare ~/Documents/GitHub). git-watcher still spans all group repos.
- bootstrap.get_claude_command: wrapper now exports CL_ANCHOR=<cwd> so OC-launched sessions satisfy the CL guard hooks (which now hard-require CL_ANCHOR, no CWD fallback). Single-repo tabs anchor at their repo; group tab at PlatformManifest.
- Added tests/test_anchor_launch.py (2 tests). NOTE: pre-existing test_watcher_pane.py failures are unrelated (confirmed on clean main).

## 2026-05-24 — Fix stale cxrp test fixtures (0.2 → 0.3)

- tests/test_cxrp_capture.py hardcoded schema_version "0.2" but cxrp is at 0.3 (envelope schema const "0.3"). Bumped the 4 envelope schema_version fixtures/assertions to "0.3"; left the separate nested $payload_schema coding_agent_target/v0.2 ref (consistent with code). Full OC suite green.

## 2026-05-24 — OC panes anchor all 3 CLIs via cl session start (Phase 3)

- bootstrap.get_{claude,codex,aider}_command now prepend a shared _CL_ANCHOR_PRELUDE (`eval "$(cl session start 2>/dev/null || true)"`) so every Console-launched CLI anchors at its repo OWNING MANIFEST (RepoGraph-resolved), not the bare cwd. Corrects the earlier hardcoded CL_ANCHOR=cwd. Repos not hooked to a manifest resolve to nothing → skipped. Updated tests/test_anchor_launch.py (asserts prelude across all 3 CLIs). 135 tests pass.

## 2026-05-27 — Fix: re-anchor claude in pane shells after session exit

`bootstrap.py`: `_CL_ANCHOR_PRELUDE` now resolves `cl` via `CL_HOME` (works in non-login shells); `get_claude_command` writes a shared `console-rc-{key}.sh` that defines `claude()` with auto-anchor, used by the post-claude shell and the shell pane.
`launcher.py`: shell pane (`while true`) uses `bash --rcfile /tmp/console-rc-{key}.sh` so typing `claude` from that pane re-anchors automatically.
`tests/test_anchor_launch.py`: updated assertion to match new prelude shape (`session start` + `_CL_BIN`).

## 2026-05-27 — Fix: source ~/.bashrc in anchor prelude (CL_HOME not in zellij pane env)

`_CL_ANCHOR_PRELUDE` now sources `~/.bashrc` before resolving `cl`. Zellij panes are non-login non-interactive shells — they don't source `~/.bashrc`, so `CL_HOME` and PATH were unset, causing `cl session start` to silently fail and `CL_ANCHOR` to stay unset.

## 2026-05-27 — Fix: revert shell pane to bash -l (bash --rcfile -i caused stuck pane)

Reverted the shell pane loop back to `while true; do bash -l; sleep 1; done`. The `bash --rcfile file -i` variant caused a stuck blinking cursor — bash with `-i` inside a zellij subshell loop does not present a prompt correctly. The `claude()` re-anchor function only needs to be in the post-claude drop-to-shell (exec bash --rcfile), not the shell pane loop.
