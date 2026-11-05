#!/bin/bash
# Launch the Destiny Grimoire MCP server (stdio) using the local venv.
# Works with Unix (.venv/bin/python) and Windows (.venv/Scripts/python.exe)
# virtualenv layouts, including Git Bash / MSYS.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=""
for candidate in "$HERE/.venv/bin/python" "$HERE/.venv/Scripts/python.exe" "$HERE/.venv/bin/python3"; do
    if [ -x "$candidate" ]; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "mcp venv missing. Run:" >&2
    echo "  bash $HERE/install.sh" >&2
    exit 1
fi
exec "$PY" "$HERE/server.py" "$@"
