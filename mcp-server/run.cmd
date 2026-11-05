@echo off
rem Launch the Destiny Grimoire MCP server (stdio) using the local venv.
rem OpenCode starts and stops this process automatically; if you run it by
rem hand, keep this window open for as long as the client needs the server.
setlocal
set "HERE=%~dp0"
set "PY=%HERE%.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%HERE%.venv\bin\python.exe"
if not exist "%PY%" set "PY=%HERE%.venv\bin\python"
if not exist "%PY%" (
    echo mcp venv missing. Run: bash "%HERE%install.sh" 1>&2
    exit /b 1
)
"%PY%" "%HERE%server.py" %*
exit /b %ERRORLEVEL%
