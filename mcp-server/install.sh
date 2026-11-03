#!/bin/bash
# Install the optional MCP adapter: create the venv and install the official SDK.
# Idempotent. Requires network access for pip.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/.venv"
PY="$VENV/bin/python"
REQ="$HERE/requirements.lock.txt"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required for the MCP adapter" >&2
    exit 1
fi

if ! python3 - <<'PY'
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
then
    echo "MCP SDK needs Python 3.10+; found $(python3 -V 2>&1)" >&2
    exit 1
fi

if [ ! -x "$PY" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --require-hashes -r "$REQ"

echo "MCP adapter ready: $HERE/run.sh"
echo ""
echo "Register it in your MCP client (OpenCode example):"
cat <<JSON
{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["$HERE/run.sh"]
      }
    }
  }
}
JSON
