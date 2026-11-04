#!/bin/bash
# Resolves an agent workspace root from the calling script's location.
# Usage: resolve-workspace.sh <calling-script-path> [drifter|eris|calus|<id>]
# Works in the Work tree, from a fresh clone via lore/ (symlink or clone), or
# anywhere the agent repo and grimoire sit in the expected relative layouts.
# Candidates are cd-canonicalized before testing because `path/../file` resolves
# PHYSICALLY through symlinks at the kernel level, which mis-parents lore/.
CALLER="$1"
AGENT="${2:-drifter}"
case "$AGENT" in
    drifter) MARKER=drifter.md; DIR=how-to-drift-for-agents ;;
    eris)    MARKER=eris.md;    DIR=eris-morn ;;
    calus)   MARKER=calus.md;   DIR=destiny-agent-calus ;;
    *)       MARKER="$AGENT.md"; DIR="$AGENT" ;;
esac
D="$(cd "$(dirname "$CALLER")" 2>/dev/null && pwd)"
[ -n "$D" ] || { echo "resolve-workspace: cannot resolve caller dir for $CALLER" >&2; exit 1; }
for C in "$D" "$D/.." "$D/../.." "$D/../../.." \
         "$D/../$DIR" "$D/../../$DIR" "$D/../../../$DIR"; do
    P="$(cd "$C" 2>/dev/null && pwd)" || continue
    [ -n "$P" ] || continue
    if [ -f "$P/$MARKER" ]; then echo "$P"; exit 0; fi
    if [ -f "$P/$DIR/$MARKER" ]; then echo "$P/$DIR"; exit 0; fi
done
echo "resolve-workspace: $AGENT workspace not found from $CALLER" >&2
exit 1
