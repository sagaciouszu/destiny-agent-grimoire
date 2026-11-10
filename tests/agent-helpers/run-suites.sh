#!/bin/bash
# Run this agent's suites from tests/suites.json (additive to master-audit.sh).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
GRIMOIRE="${GRIMOIRE:-$REPO/lore}"
exec python3 "$GRIMOIRE/tests/run-suite-manifest.py" "$REPO" "$@"
