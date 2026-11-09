#!/bin/bash
# Keep OpenClaw's MCP config pointing at the stable local grimoire wrapper.
#
# The wrapper (~/.local/bin/grimoire-mcp) delegates to the pointer symlink
# ~/.local/share/grimoire -> the live checkout. Relocating the archive only
# re-points the symlink; neither OpenClaw's config nor the wrapper changes.
#
# Usage: scripts/ensure-openclaw-mcp.sh [archive-root]
# Idempotent; exits 0 when OpenClaw is absent or already correct.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="$(cd "${1:-$HERE}" && pwd)"
OC_ROOT="${OPENCLAW_ROOT:-$HOME/.openclaw}"
CFG="$OC_ROOT/openclaw.json"
POINTER="${GRIMOIRE_POINTER:-$HOME/.local/share/grimoire}"
WRAPPER="${GRIMOIRE_WRAPPER:-$HOME/.local/bin/grimoire-mcp}"
LAUNCHER="mcp-server/run.sh"

# OpenClaw not installed: create pointer/wrapper anyway so local launchers work.
mkdir -p "$(dirname "$POINTER")" "$(dirname "$WRAPPER")"
ln -sfn "$ARCHIVE" "$POINTER"
cat > "$WRAPPER" <<W
#!/bin/bash
exec "\$HOME/.local/share/grimoire/$LAUNCHER"
W
chmod +x "$WRAPPER"

[ -f "$CFG" ] || { echo "openclaw mcp: wrapper in place; openclaw absent, nothing to write"; exit 0; }

python3 - "$CFG" "$POINTER" "$WRAPPER" <<'PY'
import json, os, shutil, sys, time
cfg_path, pointer, wrapper = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(cfg_path, encoding='utf-8') as fh:
        data = json.load(fh)
except Exception as exc:
    sys.exit(f'FATAL: cannot parse {cfg_path}: {exc}')
servers = data.setdefault('mcp', {}).setdefault('servers', {})
desired = {'command': wrapper, 'cwd': os.path.join(pointer, 'mcp-server')}
current = servers.get('grimoire')
if current == desired:
    print('openclaw mcp: grimoire already points at wrapper')
    sys.exit(0)
backup = cfg_path + '.bak-' + time.strftime('%Y%m%d-%H%M%S')
shutil.copy2(cfg_path, backup)
action = 'added' if current is None else 'updated'
servers['grimoire'] = desired
with open(cfg_path, 'w', encoding='utf-8') as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write('\n')
print(f'openclaw mcp: {action} grimoire -> {wrapper}')
print(f'openclaw mcp: backup at {os.path.basename(backup)}; restart OpenClaw to reload')
PY
