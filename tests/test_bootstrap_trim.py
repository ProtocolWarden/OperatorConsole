# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""Tests for the hot-trim of the compiled log section (bootstrap._trim_log)."""

from __future__ import annotations

from operator_console.bootstrap import _trim_log

_LOG = """# Log

## 2026-01-01 — first
oldest entry body

## 2026-01-02 — second
body

## 2026-01-03 — third
body

## 2026-01-04 — fourth
body

## 2026-01-05 — fifth
newest entry body
"""


def test_trim_keeps_recent_tail_and_pointer():
    out = _trim_log(_LOG, max_entries=2)
    # preamble kept
    assert out.startswith("# Log")
    # newest two kept (newest-last convention)
    assert "fourth" in out and "fifth" in out
    # older dropped
    assert "first" not in out and "second" not in out and "third" not in out
    # pointer present with correct omitted count (3 of 5)
    assert "3 older entries omitted" in out
    assert ".console/log.md" in out


def test_no_trim_when_under_limit():
    out = _trim_log(_LOG, max_entries=10)
    assert out == _LOG  # unchanged: 5 entries <= 10


def test_disabled_with_nonpositive():
    assert _trim_log(_LOG, max_entries=0) == _LOG


def test_unrecognized_shape_unchanged():
    plain = "just some text with no headings\n"
    assert _trim_log(plain, max_entries=2) == plain


def test_singular_pointer_grammar():
    out = _trim_log(_LOG, max_entries=4)  # omit exactly 1
    assert "1 older entry omitted" in out


_BACKLOG = """# Backlog

## In Progress

- [ ] active thing

## Up Next

- [ ] next thing

## Done

- [x] done 1
- [x] done 2
- [x] done 3

---
_footer_
"""


def test_backlog_done_trimmed_active_kept():
    from operator_console.bootstrap import _trim_backlog
    out = _trim_backlog(_BACKLOG)
    assert "active thing" in out          # In Progress kept
    assert "next thing" in out            # Up Next kept
    assert "done 1" not in out            # completed inventory dropped
    assert "historical/completed backlog section(s) omitted" in out
    assert ".console/backlog.md" in out


def test_backlog_drops_historical_sections_keeps_unknown():
    from operator_console.bootstrap import _trim_backlog
    txt = (
        "# Backlog\n\n## In Progress\n- [ ] a\n\n"
        "## Recently Completed (Stage Cycles)\n- [x] r\n\n"
        "## Previously In Progress\n- [x] p\n\n"
        "## Cycle 36 updates (2026-05-28)\n- note\n\n"
        "## Custom Section\n- keep me\n\n## Up Next\n- [ ] b\n"
    )
    out = _trim_backlog(txt)
    assert "- [ ] a" in out and "- [ ] b" in out   # active kept
    assert "keep me" in out                         # unrecognized section kept
    assert "Recently Completed" not in out
    assert "Previously In Progress" not in out
    assert "Cycle 36 updates" not in out
    assert "3 historical/completed backlog section(s) omitted" in out


def test_backlog_no_done_unchanged():
    from operator_console.bootstrap import _trim_backlog
    txt = "# Backlog\n\n## In Progress\n\n- [ ] x\n"
    assert _trim_backlog(txt) == txt
