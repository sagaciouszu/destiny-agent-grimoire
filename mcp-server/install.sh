#!/bin/bash
# Install the optional MCP adapter: create the venv and install the official SDK.
# Idempotent. Requires network access for pip. Works on Unix and Windows
# (Git Bash / MSYS virtualenv layouts).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/.venv"
REQ="$HERE/requirements.lock.txt"

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "python3 is required for the MCP adapter" >&2
    exit 1
fi

if ! "$PYTHON" - <<'PY'
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
then
    echo "MCP SDK needs Python 3.10+; found $("$PYTHON" -V 2>&1)" >&2
    exit 1
fi

if [ ! -x "$VENV/bin/python" ] && [ ! -x "$VENV/Scripts/python.exe" ]; then
    "$PYTHON" -m venv "$VENV"
fi

# Resolve the venv interpreter for both Unix and Windows layouts.
VPY=""
for candidate in "$VENV/bin/python" "$VENV/Scripts/python.exe"; do
    if [ -x "$candidate" ]; then
        VPY="$candidate"
        break
    fi
done
if [ -z "$VPY" ]; then
    echo "venv created but no interpreter found under $VENV" >&2
    exit 1
fi
"$VPY" -m pip install -q --require-hashes -r "$REQ"

# Pick the launcher and config path the current platform can execute.
case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
        LAUNCHER="run.cmd"
        if command -v cygpath >/dev/null 2>&1; then
            CONFIG_PATH="$(cygpath -w "$HERE/run.cmd")"
        else
            CONFIG_PATH="mcp-server\\run.cmd"
        fi ;;
    *)
        LAUNCHER="run.sh"
        CONFIG_PATH="$HERE/run.sh" ;;
esac

echo "MCP adapter ready: $HERE/$LAUNCHER"
echo ""
echo "The server is a stdio process: your client starts it and must keep it"
echo "running while it is in use. OpenCode launches and stops it automatically."
echo ""
echo "Register it in your MCP client (OpenCode example):"
cat <<JSON
{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["$CONFIG_PATH"]
      }
    }
  }
}
JSON
