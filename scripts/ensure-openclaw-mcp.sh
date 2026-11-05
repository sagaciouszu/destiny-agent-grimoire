#!/bin/bash
# Ensure OpenClaw's config carries an absolute grimoire MCP entry.
#
# OpenClaw's update doctor starts MCP servers to validate their tool schemas.
# A bare `run.sh` cannot be resolved from the doctor's working directory and is
# reported as "not started for update validation". This helper upserts the
# entry with an absolute path, backing up the config first. Idempotent:
# an already-correct config is left byte-for-byte untouched.
#
# Usage: scripts/ensure-openclaw-mcp.sh [archive-root]
# Exits 0 when OpenClaw is absent or the config is already correct.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVE="$(cd "${1:-$HERE}" && pwd)"
OC_ROOT="${OPENCLAW_ROOT:-$HOME/.openclaw}"
CFG="$OC_ROOT/openclaw.json"

# OpenClaw not installed or not configured: nothing to do.
[ -f "$CFG" ] || exit 0

LAUNCHER="mcp-server/run.sh"
case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*) LAUNCHER="mcp-server/run.cmd" ;;
esac

python3 - "$CFG" "$ARCHIVE" "$LAUNCHER" <<'PY'
import json, os, shutil, sys, time

cfg_path, archive, launcher = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
command = os.path.join(archive, launcher)
cwd = os.path.join(archive, 'mcp-server')

try:
    with open(cfg_path, encoding='utf-8') as fh:
        data = json.load(fh)
except Exception as exc:  # noqa: BLE001
    sys.exit(f'FATAL: cannot parse {cfg_path}: {exc}')

servers = data.setdefault('mcp', {}).setdefault('servers', {})
desired = {'command': command, 'cwd': cwd}
current = servers.get('grimoire')

if current == desired:
    print('openclaw mcp: grimoire already configured with an absolute path')
    sys.exit(0)

backup = cfg_path + '.bak-' + time.strftime('%Y%m%d-%H%M%S')
shutil.copy2(cfg_path, backup)
action = 'added' if current is None else 'updated'
servers['grimoire'] = desired
with open(cfg_path, 'w', encoding='utf-8') as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write('\n')
print(f'openclaw mcp: {action} grimoire -> {command}')
print(f'openclaw mcp: backup at {os.path.basename(backup)}; restart OpenClaw to reload')
PY
