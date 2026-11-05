#!/bin/bash
# One-command MCP handshake probe (Unix launcher).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=""
for candidate in "$HERE/.venv/bin/python" "$HERE/.venv/Scripts/python.exe" "$HERE/.venv/bin/python3" python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
        PY="$candidate"
        break
    fi
done
exec "$PY" "$HERE/probe.py" "$@"
