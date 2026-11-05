# Launch the Destiny Grimoire MCP server (stdio) using the local venv.
# PowerShell equivalent of run.cmd for clients that prefer pwsh/powershell.
#
# Client config example:
#   "command": ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
#               "-File", "lore\\mcp-server\\run.ps1"]
#
# The server is a stdio process: the client starts it and must keep it running
# while it is in use. Closing this window drops the connection.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }

$candidates = @(
    (Join-Path $here '.venv\Scripts\python.exe'),
    (Join-Path $here '.venv\bin\python.exe'),
    (Join-Path $here '.venv\bin\python')
)
$py = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $py) {
    [Console]::Error.WriteLine('mcp venv missing. Run:')
    [Console]::Error.WriteLine("  bash `"$here/install.sh`"")
    exit 1
}

& $py (Join-Path $here 'server.py') @args
exit $LASTEXITCODE
