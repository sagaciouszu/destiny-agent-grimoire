#!/usr/bin/env python3
"""Guard the per-agent suite manifests against accidental loss.

Checks:
  - tests/master-audit.sh and tests/suites.json list the same suites/commands
  - the central series/suite-baseline.json baseline is a subset of each manifest
  - suite counts never drop below the baseline
  - tiers and required fields are valid

Additions pass. Removals and silent rewrites fail.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, 'series', 'suite-baseline.json')
TIERS = {'core', 'persona', 'experimental'}


def audit_suites(agent):
    path = os.path.join(agent, 'tests', 'master-audit.sh')
    text = open(path, encoding='utf-8').read()
    block = re.search(r'SUITES=\((.*?)\n\)', text, re.S)
    if not block:
        raise AssertionError('SUITES block not found')
    out = []
    for entry in re.findall(r'"([^"]+)"', block.group(1)):
        name, command = entry.split('|', 1)
        out.append((name.strip(), command.strip()))
    return out


def main():
    baseline = json.load(open(BASELINE, encoding='utf-8'))
    failures = []
    present = 0
    for agent_name, spec in baseline['agents'].items():
        agent = os.path.abspath(os.path.join(ROOT, '..', agent_name))
        manifest_path = os.path.join(agent, 'tests', 'suites.json')
        if not os.path.isdir(agent):
            # CI checks out this repository alone; agent repos are siblings
            # only on a full workspace. Skip absent agents, verify present ones.
            print(f'  {agent_name}: skipped (repository not present)')
            continue
        present += 1
        try:
            manifest = json.load(open(manifest_path, encoding='utf-8'))
            suites = manifest['suites']
            audit = audit_suites(agent)
        except Exception as exc:  # noqa: BLE001
            failures.append(f'{agent_name}: {exc}')
            continue

        names = [s.get('name') for s in suites]
        if len(names) != len(set(names)):
            failures.append(f'{agent_name}: duplicate suite names')
        if len(suites) != len(audit):
            failures.append(f'{agent_name}: manifest {len(suites)} != audit {len(audit)}')
        if [(s['name'], s['command']) for s in suites] != audit:
            failures.append(f'{agent_name}: manifest and master-audit commands differ')
        missing = set(spec['required']) - set(names)
        if missing:
            failures.append(f'{agent_name}: baseline suites missing: {sorted(missing)}')
        if len(suites) < spec['count']:
            failures.append(f'{agent_name}: suite count {len(suites)} < baseline {spec["count"]}')
        for suite in suites:
            if not suite.get('name') or not suite.get('command'):
                failures.append(f'{agent_name}: suite missing name/command')
            if suite.get('tier') not in TIERS:
                failures.append(f'{agent_name}: bad tier for {suite.get("name")}')

        print(f'  {agent_name}: {len(suites)} suites, baseline {spec["count"]}')

    if failures:
        print('\nFAIL:')
        for failure in failures:
            print(f'  - {failure}')
        return 1
    if present == 0:
        print('  SKIP: no agent repositories present to check')
        return 0
    print(f'  PASS: {present} agent manifests match their audits and baseline')
    return 0


if __name__ == '__main__':
    sys.exit(main())
