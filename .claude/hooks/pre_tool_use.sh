#!/usr/bin/env bash
set -euo pipefail
CL_BIN="${CL_HOME:+$CL_HOME/bin/cl}"
CL_BIN="${CL_BIN:-$(command -v cl 2>/dev/null || true)}"
if [[ -z "$CL_BIN" || ! -x "$CL_BIN" ]]; then
  echo "ContextLifecycle: cl not found. Set CL_HOME to the CL repo root or install cl on PATH." >&2
  exit 1
fi
exec "$CL_BIN" hook pre_tool_use "$@"
