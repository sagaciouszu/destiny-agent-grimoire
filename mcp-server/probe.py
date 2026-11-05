#!/usr/bin/env python3
"""One-command MCP handshake probe.

Starts the grimoire MCP server the way a client would, performs
initialize -> initialized -> tools/list, and reports the tools it exposes.
Exit 0 on a healthy handshake, non-zero otherwise.

Usage:
    python3 mcp-server/probe.py
    bash mcp-server/probe.sh
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROTOCOL = '2024-11-05'


def launcher(mode='auto'):
    """Resolve the spawn command for a launcher mode.

    auto: run.cmd on Windows, run.sh elsewhere. Explicit modes let CI exercise
    every launcher on its native platform (probe.py --launcher ps1)."""
    if mode == 'ps1':
        ps1 = os.path.join(HERE, 'run.ps1')
        if not os.path.exists(ps1):
            raise SystemExit('run.ps1 missing')
        exe = shutil.which('powershell') or shutil.which('powershell.exe') or 'powershell'
        return [exe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps1]
    if mode == 'sh':
        sh = os.path.join(HERE, 'run.sh')
        if not os.access(sh, os.X_OK):
            raise SystemExit('run.sh missing or not executable')
        return [sh]
    cmd = os.path.join(HERE, 'run.cmd')
    if not os.path.exists(cmd):
        raise SystemExit('run.cmd missing')
    if os.name == 'nt':
        return ['cmd', '/c', cmd]
    # Non-Windows fallback: Git Bash can execute the .cmd via cmd.exe only on
    # Windows, so fall back to the shell launcher.
    return launcher('sh')


def send(proc, payload):
    proc.stdin.write(json.dumps(payload) + '\n')
    proc.stdin.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launcher', choices=('auto', 'cmd', 'ps1', 'sh'),
                        default='auto', help='which launcher to exercise')
    args = parser.parse_args()
    proc = subprocess.Popen(
        launcher(args.launcher), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, cwd=HERE)
    try:
        send(proc, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                    'params': {'protocolVersion': PROTOCOL, 'capabilities': {},
                               'clientInfo': {'name': 'grimoire-probe', 'version': '1'}}})
        send(proc, {'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        send(proc, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
        tools = None
        for _ in range(200):
            line = proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get('id') == 2:
                if 'error' in msg:
                    raise SystemExit(f'tools/list error: {msg["error"]}')
                tools = msg['result'].get('tools', [])
                break
        if tools is None:
            err = proc.stderr.read() if proc.poll() is not None else ''
            raise SystemExit(f'no tools/list response {err[:500]}')
        print(f'OK: grimoire MCP server responded with {len(tools)} tools')
        print('tools: ' + ', '.join(sorted(t['name'] for t in tools)))
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == '__main__':
    sys.exit(main())
