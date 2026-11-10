#!/bin/bash
# Resolves an agent workspace root from the calling script's location.
# Usage: resolve-workspace.sh <calling-script-path> [agent-id]
# Works in the Work tree, from a fresh clone via lore/ (symlink or clone), or
# anywhere the agent repo and grimoire sit in the expected relative layouts.
# The agent id and repository come from series/agents.json; when the id is
# omitted it is inferred from the caller's repository directory. There is no
# default persona.
# Candidates are cd-canonicalized before testing because `path/../file` resolves
# PHYSICALLY through symlinks at the kernel level, which mis-parents lore/.
CALLER="$1"
AGENT="${2:-}"
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REG="$HERE/../series/agents.json"

META="$(python3 - "$REG" "$AGENT" "$CALLER" <<'PY'
import json
import os
import sys

registry, agent, caller = sys.argv[1:4]
rows = []
if os.path.isfile(registry):
    with open(registry, encoding="utf-8") as fh:
        rows = json.load(fh).get("agents", [])

if not agent:
    path = os.path.abspath(os.path.dirname(caller))
    while path and path != os.path.dirname(path):
        base = os.path.basename(path)
        for row in rows:
            if row.get("source") == base:
                agent = row.get("id", "")
                break
        if agent:
            break
        path = os.path.dirname(path)

if not agent:
    raise SystemExit(1)

for row in rows:
    if row.get("id") == agent:
        print(row.get("source") or ("destiny-agent-" + agent))
        print(row.get("entry") or (agent + ".md"))
        raise SystemExit(0)

# Registry absent or the row is new: keep the conventional layout.
print("destiny-agent-" + agent)
print(agent + ".md")
PY
)" || { echo "resolve-workspace: cannot infer an agent id for $CALLER" >&2; exit 1; }

DIR="$(printf '%s\n' "$META" | sed -n '1p')"
MARKER="$(printf '%s\n' "$META" | sed -n '2p')"

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
