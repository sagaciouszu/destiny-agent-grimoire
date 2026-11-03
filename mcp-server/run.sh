#!/bin/bash
# Launch the Destiny Grimoire MCP server (stdio) using the local venv.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "mcp venv missing. Run:" >&2
    echo "  python3 -m venv $HERE/.venv" >&2
    echo "  $HERE/.venv/bin/pip install -r $HERE/requirements.txt" >&2
    exit 1
fi
exec "$PY" "$HERE/server.py" "$@"
