#!/usr/bin/env bash
# setup.sh — install OperatorConsole's repo wrapper as a shell command.
#
# Also provisions the dev machine (CL_HOME, RepoGraph registry, adapter hooks)
# via PlatformManifest/scripts/provision-machine.sh if it exists.
# Pass --skip-provision to run only the OC-local bootstrap steps.

set -euo pipefail

CONSOLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITHUB_DIR="$(cd "$CONSOLE_DIR/.." && pwd)"

SKIP_PROVISION=false
PROVISION_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-provision) SKIP_PROVISION=true; shift ;;
    --with-private)   PROVISION_ARGS+=("--with-private"); shift ;;
    --force-hooks)    PROVISION_ARGS+=("--force-hooks"); shift ;;
    *) echo "setup.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

echo "▶ OperatorConsole setup"
echo "  repo: $CONSOLE_DIR"
echo ""

bash "$CONSOLE_DIR/bootstrap.sh"
"$CONSOLE_DIR/console" symlink

PROVISION_SH="$GITHUB_DIR/PlatformManifest/scripts/provision-machine.sh"
if [[ "$SKIP_PROVISION" == false && -f "$PROVISION_SH" ]]; then
  echo ""
  bash "$PROVISION_SH" "${PROVISION_ARGS[@]}"
else
  echo ""
  echo "  (skipping machine provision — run PlatformManifest/scripts/provision-machine.sh separately)"
fi
