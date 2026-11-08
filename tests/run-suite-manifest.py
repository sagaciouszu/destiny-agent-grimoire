#!/usr/bin/env python3
"""Run an agent's suites from tests/suites.json.

The manifest is the same command list as tests/master-audit.sh, so this runner
adds a stable interface without replacing the existing audit. Every command
runs with HERE/REPO/LORE/WORKSPACE exported, matching master-audit.sh.

Usage:
    python3 tests/run-suite-manifest.py ../destiny-agent-eris-morn
    python3 tests/run-suite-manifest.py ../destiny-agent-eris-morn --tier core
    python3 tests/run-suite-manifest.py ../destiny-agent-eris-morn --list
"""
import argparse
import json
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('agent', help='agent repository directory')
    parser.add_argument('--tier', choices=('core', 'persona', 'experimental'),
                        help='run only one tier')
    parser.add_argument('--list', action='store_true', help='list suites only')
    parser.add_argument('--dry-run', action='store_true', help='print commands only')
    args = parser.parse_args()

    agent = os.path.abspath(os.path.expanduser(args.agent))
    manifest_path = os.path.join(agent, 'tests', 'suites.json')
    if not os.path.exists(manifest_path):
        raise SystemExit(f'manifest not found: {manifest_path}')
    data = json.load(open(manifest_path, encoding='utf-8'))
    suites = data.get('suites', [])
    if args.tier:
        suites = [s for s in suites if s.get('tier') == args.tier]
    if not suites:
        raise SystemExit('no suites selected')

    env = os.environ.copy()
    env['HERE'] = os.path.join(agent, 'tests')
    env['REPO'] = agent
    env['WORKSPACE'] = os.environ.get('WORKSPACE', agent)
    env['LORE'] = os.environ.get('LORE', os.path.join(agent, 'lore'))

    print(f'{data.get("agent", os.path.basename(agent))}: {len(suites)} suites')
    passed = failed = 0
    for suite in suites:
        name, command = suite['name'], suite['command']
        if args.list:
            print(f'  [{suite.get("tier", "core")}] {name}')
            continue
        if args.dry_run:
            print(f'  {name}: {command}')
            continue
        ok = subprocess.run(command, shell=True, cwd=agent, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        print(f'  {"✓" if ok else "✗"} [{suite.get("tier", "core")}] {name}')
        passed += ok
        failed += not ok

    if args.list or args.dry_run:
        return 0
    print(f'  SCORECARD: {passed} / {len(suites)} suites passed ({failed} failed)')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
