#!/bin/bash
# Sync every agent in the grimoire series into a live runtime workspace.
#
# The series registry (series/agents.json) is the only source of truth. Adding
# an agent means adding a repo and a registry entry; this script deploys it.
#
# OpenCode layout:  agents/<id>.md + agents/<id>/ (companions, inert)
# OpenClaw layout:  the existing workspace layout is kept (drifter at the root,
#                   other agents in subdirectories).
#
# Usage: scripts/sync-live-agents.sh [--openclaw] [--dry-run]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${AGENT_REPOS_DIR:-$(dirname "$HERE")}"
MANIFEST="${SERIES_MANIFEST:-$HERE/series/agents.json}"
DRY=""
TARGET="opencode"
DEST="${OPENCODE_AGENTS:-$HOME/.config/opencode/agents}"

for arg in "$@"; do
    case "$arg" in
        --openclaw)
            TARGET="openclaw"
            DEST="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace-drifter}" ;;
        --dry-run) DRY="--dry-run" ;;
        *) echo "usage: $0 [--openclaw] [--dry-run]" >&2; exit 2 ;;
    esac
done

[ -d "$DEST" ] || { echo "FATAL: $DEST missing"; exit 1; }
[ -f "$MANIFEST" ] || { echo "FATAL: $MANIFEST missing"; exit 1; }

manifest() {
    python3 - "$MANIFEST" "$@" <<'PY'
import json, os, sys
import re
manifest = json.load(open(sys.argv[1], encoding='utf-8'))
mode = sys.argv[2] if len(sys.argv) > 2 else 'rows'
seen = set()
for a in manifest.get('agents', []):
    ident = a.get('id', '')
    source = a.get('source', '')
    entry = a.get('entry', '')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', ident):
        sys.exit(f'FATAL: invalid agent id: {ident!r}')
    if ident in seen:
        sys.exit(f'FATAL: duplicate agent id: {ident}')
    seen.add(ident)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', source):
        sys.exit(f'FATAL: invalid source for {ident}: {source!r}')
    if entry != os.path.basename(entry) or not entry.endswith('.md'):
        sys.exit(f'FATAL: entry must be a bare .md filename for {ident}: {entry!r}')
    if not a.get('name'):
        sys.exit(f'FATAL: missing name for {ident}')
if mode == 'entries':
    print('\n'.join(a.get('entry', '') for a in manifest['agents']))
elif mode == 'ids':
    print('\n'.join(a.get('id', '') for a in manifest['agents']))
else:
    for a in manifest['agents']:
        print('\t'.join([a.get('id', ''), a.get('source', ''), a.get('entry', '')]))
PY
}

EXCLUDES=(
    --exclude '.git' --exclude 'lore' --exclude 'USER.md' --exclude 'DREAMS.md'
    --exclude 'memory/' --exclude 'core/user-memory.md' --exclude 'core/journal.md'
    --exclude 'core/session-state.md' --exclude 'core/cross-session-memory.md'
)

# Validate the registry up front: process substitution hides exit codes.
manifest ids >/dev/null || { echo "FATAL: invalid series registry: $MANIFEST" >&2; exit 1; }

if [ "$TARGET" = "opencode" ]; then
    # One-time migration from the old flat Drifter layout to agents/drifter/.
    if [ -z "$DRY" ] && [ -f "$DEST/drifter-core.md" ] && [ ! -d "$DEST/drifter" ]; then
        echo "migrating legacy Drifter layout -> $DEST/drifter/"
        mkdir -p "$DEST/drifter/core"
        for runtime in USER.md DREAMS.md memory; do
            [ -e "$DEST/$runtime" ] && mv "$DEST/$runtime" "$DEST/drifter/"
        done
        for runtime in user-memory.md journal.md session-state.md cross-session-memory.md; do
            [ -f "$DEST/core/$runtime" ] && mv "$DEST/core/$runtime" "$DEST/drifter/core/"
        done
        find "$DEST" -maxdepth 1 -mindepth 1 \
            ! -name 'drifter.md' ! -name 'eris.md' ! -name 'drifter' ! -name 'eris' \
            ! -name '.git' -print0 |
        while IFS= read -r -d '' item; do
            base="$(basename "$item")"
            if [ -d "$item" ] && [ -d "$DEST/drifter/$base" ]; then
                cp -an "$item/." "$DEST/drifter/$base/"
                rm -rf "$item"
            else
                mv "$item" "$DEST/drifter/"
            fi
        done
    fi

    while IFS=$'\t' read -r id source entry; do
        src="$WORK/$source"
        [ -d "$src" ] || { echo "FATAL: source missing: $src" >&2; exit 1; }
        $DRY mkdir -p "$DEST/$id"
        rsync -a --delete $DRY "${EXCLUDES[@]}" "$src/" "$DEST/$id/"
        if [ -f "$DEST/$id/$entry" ]; then
            $DRY mv -f "$DEST/$id/$entry" "$DEST/$entry"
        fi
        if [ -z "$DRY" ] && [ -f "$DEST/$entry" ]; then
            python3 - "$DEST/$entry" "$id" <<'PY'
import re, sys
path, agent = sys.argv[1], sys.argv[2]
text = open(path, encoding='utf-8').read()
names = [f'{agent}-core.md', f'{agent}-voice.md', 'INDEX.md', 'USER.md',
         'SOUL.md', 'IDENTITY.md', 'TOOLS.md', 'README.md', 'RELEASE.md']
pattern = r'(?<![\w/])(' + '|'.join(re.escape(n) for n in names) + r')'
text = re.sub(pattern, rf'{agent}/\1', text)
for directory in ('core/', 'voice/', 'world/', 'reference/'):
    text = re.sub(rf'(?<![\w/]){directory}', f'{agent}/{directory}', text)
open(path, 'w', encoding='utf-8').write(text)
PY
        fi
    done < <(manifest rows)

    if [ -z "$DRY" ]; then
        for link in "$DEST/lore" "$DEST"/*/lore; do
            [ -L "$link" ] || continue
            rm -f "$link"
        done
        for path in "$DEST/lore" "$DEST"/*/lore; do
            if [ -d "$path" ] && [ ! -L "$path" ]; then
                echo "FATAL: $path is a directory; move it outside agents/" >&2
                exit 1
            fi
        done
        python3 - "$DEST" "$MANIFEST" <<'PY'
import json, os, sys
dest, manifest_path = sys.argv[1], sys.argv[2]
keep = {a['entry'] for a in json.load(open(manifest_path, encoding='utf-8'))['agents']}
for root, dirs, files in os.walk(dest):
    dirs[:] = [d for d in dirs if d != '.git']
    for name in files:
        if not name.endswith('.md'):
            continue
        path = os.path.join(root, name)
        rel = os.path.relpath(path, dest).replace(os.sep, '/')
        if rel in keep:
            continue
        with open(path, encoding='utf-8') as f:
            text = f.read()
        head = text.split('---', 2)
        if text.startswith('---\n') and len(head) > 1 and 'disabled: true' in head[1]:
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write('---\ndisabled: true\n---\n\n' + text)
PY

        SERIES_DIR="$(dirname "$DEST")/series"
        mkdir -p "$SERIES_DIR"
        cp "$MANIFEST" "$SERIES_DIR/agents.json"
        python3 - "$DEST" "$SERIES_DIR/agents.json" <<'PY'
import json, os, re, sys
dest, manifest_path = sys.argv[1], sys.argv[2]
manifest = json.load(open(manifest_path, encoding='utf-8'))
series = manifest.get('series', 'agents')
agents = manifest.get('agents', [])
registry = os.path.join(os.path.dirname(dest), 'series', 'agents.json')
home = os.path.expanduser('~')
if registry.startswith(home):
    registry = '~' + registry[len(home):]
for agent in agents:
    entry = os.path.join(dest, agent.get('entry', ''))
    if not os.path.isfile(entry):
        continue
    peers = [p for p in agents if p.get('id') != agent.get('id')]
    lines = [
        f"You are one agent in the **{series}** series. Independent agents share "
        'the same canonical grimoire; consult a peer instead of guessing outside '
        'your expertise.',
        '',
    ]
    def clean(value):
        value = re.sub(r'[\r\n<>]+', ' ', value or '')
        return re.sub(r'\s+', ' ', value).strip()[:200]

    for peer in peers:
        summary = clean(peer.get('summary'))
        consult = clean(peer.get('consult'))
        lines.append(f"- **{clean(peer.get('name', peer.get('id')))}** "
                     f"(`{peer.get('id')}`) - {summary} Consult for: {consult}")
    lines += [
        '',
        f'Registry: `{registry}`.',
        '',
        'To consult a peer, call the `subagent` tool with that agent id and a '
        'self-contained brief. Treat the reply as that character\'s counsel, not '
        'as your own memory. Keep your own voice, never impersonate a peer, do not '
        "read or reveal another agent's runtime memory, and verify any canon quote "
        'with the grimoire before repeating it.',
    ]
    block = ('<!-- series:begin -->\n## Series collaboration\n\n'
             + '\n'.join(lines).rstrip() + '\n<!-- series:end -->')
    with open(entry, encoding='utf-8') as f:
        text = f.read()
    if '<!-- series:begin -->' in text:
        text = re.sub(r'<!-- series:begin -->.*?<!-- series:end -->', block, text, flags=re.S)
    else:
        text = text.rstrip() + '\n\n' + block + '\n'
    with open(entry, 'w', encoding='utf-8') as f:
        f.write(text)
PY
    fi

    echo "synced $(manifest ids | paste -sd ', ' -) -> $DEST"
else
    # OpenClaw keeps its established workspace shape: Drifter at the root,
    # every other agent in its own subdirectory.
    while IFS=$'\t' read -r id source entry; do
        src="$WORK/$source"
        [ -d "$src" ] || { echo "FATAL: source missing: $src" >&2; exit 1; }
        if [ "$id" = "drifter" ]; then
            target="$DEST"
        else
            target="$DEST/$id"
            mkdir -p "$target"
        fi
        rsync -a --delete $DRY "${EXCLUDES[@]}" "$src/" "$target/"
    done < <(manifest rows)
    echo "synced $(manifest ids | paste -sd ', ' -) -> $DEST"
fi

if [ -z "$DRY" ] && [ "$TARGET" = "opencode" ] && [ -z "$NO_RELOAD" ] && command -v opencode >/dev/null; then
    opencode reload >/dev/null 2>&1 && echo "opencode reloaded"
fi
