#!/usr/bin/env python3
"""One-command MCP handshake probe.

Starts the grimoire MCP server the way a client would, performs
initialize -> initialized -> tools/list, and reports the tools it exposes.
Exit 0 on a healthy handshake, non-zero otherwise.

Usage:
    python3 mcp-server/probe.py
    bash mcp-server/probe.sh
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROTOCOL = '2024-11-05'


def launcher():
    if os.name == 'nt':
        cmd = os.path.join(HERE, 'run.cmd')
        if not os.path.exists(cmd):
            raise SystemExit('run.cmd missing')
        return ['cmd', '/c', cmd]
    sh = os.path.join(HERE, 'run.sh')
    if not os.access(sh, os.X_OK):
        raise SystemExit('run.sh missing or not executable')
    return [sh]


def send(proc, payload):
    proc.stdin.write(json.dumps(payload) + '\n')
    proc.stdin.flush()


def main():
    proc = subprocess.Popen(
        launcher(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
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
