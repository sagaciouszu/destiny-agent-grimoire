#!/bin/bash
# Resolves the Drifter agent workspace root from the calling script's location.
# Works in the Work tree, from a fresh clone via the lore/ symlink, or anywhere
# the agent repo and grimoire sit in the expected relative layouts.
# Candidates are cd-canonicalized before testing because `path/../file` resolves
# PHYSICALLY through symlinks at the kernel level, which mis-parents lore/.
# Usage: resolve-workspace.sh <calling-script-path>
CALLER="$1"
D="$(cd "$(dirname "$CALLER")" 2>/dev/null && pwd)"
[ -n "$D" ] || { echo "resolve-workspace: cannot resolve caller dir for $CALLER" >&2; exit 1; }
for C in "$D" "$D/.." "$D/../.." "$D/../how-to-drift-for-agents" "$D/../../how-to-drift-for-agents"; do
    P="$(cd "$C" 2>/dev/null && pwd)" || continue
    [ -n "$P" ] || continue
    if [ -f "$P/drifter.md" ]; then echo "$P"; exit 0; fi
    if [ -f "$P/how-to-drift-for-agents/drifter.md" ]; then echo "$P/how-to-drift-for-agents"; exit 0; fi
done
echo "resolve-workspace: drifter workspace not found from $CALLER" >&2
exit 1
