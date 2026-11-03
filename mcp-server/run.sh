#!/bin/bash
# Launch the Destiny Grimoire MCP server (stdio) using the local venv.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "mcp venv missing. Run:" >&2
    echo "  bash $HERE/install.sh" >&2
    exit 1
fi
exec "$PY" "$HERE/server.py" "$@"
