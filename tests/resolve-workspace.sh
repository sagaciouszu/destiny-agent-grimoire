#!/bin/bash
# Resolves the Drifter agent workspace root from the calling script's location.
# Works in the Work tree, from a fresh clone via the lore/ symlink, or anywhere
# the agent repo and grimoire sit in the expected relative layouts.
# Usage: resolve-workspace.sh <calling-script-path>
CALLER="$1"
D="$(cd "$(dirname "$CALLER")" && pwd)"
for C in "$D" "$D/.." "$D/../.." "$D/../how-to-drift-for-agents" "$D/../../how-to-drift-for-agents"; do
    if [ -f "$C/drifter.md" ]; then (cd "$C" && pwd); exit 0; fi
    if [ -f "$C/how-to-drift-for-agents/drifter.md" ]; then (cd "$C/how-to-drift-for-agents" && pwd); exit 0; fi
done
echo "resolve-workspace: drifter workspace not found from $CALLER" >&2
exit 1
