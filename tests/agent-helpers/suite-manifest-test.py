#!/usr/bin/env python3
"""Guard this agent's suite manifest (tests/suites.json) against drift from
tests/master-audit.sh.

Checks, for the invoking agent only:
  - tests/master-audit.sh and tests/suites.json list the same suite names, in
    the same order, with the same commands
  - duplicates are rejected
  - every declared tier is one of core/persona/experimental
  - suite count is at least the agent's registered baseline in lore
    series/suite-baseline.json (missing entry => template default of 18);
    additions pass

Additional suites are fine; the manifest is an additive registry.
Exit code 0 on pass, 1 on fail.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(HERE, 'suites.json')
AUDIT = os.path.join(HERE, 'master-audit.sh')
TIERS = {'core', 'persona', 'experimental'}
BASELINE = os.path.join(REPO, '..', 'lore', 'series', 'suite-baseline.json')
if not os.path.isfile(BASELINE):
    BASELINE = os.path.join(REPO, 'lore', 'series', 'suite-baseline.json')

def parse_audit(path):
    text = open(path, encoding='utf-8').read()
    block = re.search(r'SUITES=\((.*?)\n\)', text, re.S)
    if not block:
        helpers = re.findall(r'(?:source|\.)\s+"\$HERE/([^"]+)"', text)
        for helper in helpers:
            helper_path = os.path.join(HERE, helper)
            if not os.path.isfile(helper_path):
                continue
            helper_text = open(helper_path, encoding='utf-8').read()
            block = re.search(r'SUITES=\((.*?)\n\)', helper_text, re.S)
            if block:
                break
    if not block:
        raise ValueError('SUITES block not found')
    out = []
    for entry in re.findall(r'"([^"]+)"', block.group(1)):
        name, command = entry.split('|', 1)
        out.append((name.strip(), command.strip()))
    return out

def main():
    try:
        manifest = json.load(open(MANIFEST, encoding='utf-8'))
    except Exception as exc:
        print(f'FAIL: cannot parse {MANIFEST}: {exc}')
        return 1

    try:
        audit = parse_audit(AUDIT)
    except Exception as exc:
        print(f'FAIL: cannot parse {AUDIT}: {exc}')
        return 1

    suites = manifest.get('suites', [])
    failures = []

    # required agent-specific fields
    if not manifest.get('agent'):
        failures.append('manifest missing agent field')
    if manifest.get('count') != len(suites):
        failures.append(f'manifest count {manifest.get("count")} != {len(suites)} suite entries')

    names = [s.get('name') for s in suites]
    if len(set(names)) != len(names):
        failures.append('duplicate suite names in manifest')
    for i, s in enumerate(suites):
        if not s.get('name') or not s.get('command'):
            failures.append(f'suite at index {i} missing name/command')
        if s.get('tier') not in TIERS:
            failures.append(f"bad tier for {s.get('name')}: {s.get('tier')!r}")

    audit_map = dict(audit)
    manifest_map = dict((s.get('name'), s.get('command')) for s in suites)
    for name, cmd in audit:
        if manifest_map.get(name) != cmd:
            failures.append(f'command mismatch for {name}:\n    audit    = {cmd}\n    manifest = {manifest_map.get(name)}')
    for name in manifest_map:
        if name not in audit_map:
            failures.append(f'manifest suite {name} not present in master-audit.sh')
    if [n for n, _ in audit] != names:
        failures.append('order mismatch: master-audit.sh and suites.json list suites in different orders')

    # baseline coverage (if available): require lore's baseline, else template default
    agent = os.path.basename(REPO)
    minimum = 18
    if os.path.isfile(BASELINE):
        try:
            data = json.load(open(BASELINE, encoding='utf-8'))
            spec = data.get('agents', {}).get(agent)
            if spec:
                minimum = spec.get('count', minimum)
                required = set(spec.get('required', []))
                missing = required - set(names)
                if missing:
                    failures.append(f'baseline suites missing: {sorted(missing)}')
        except Exception as exc:
            print(f'  (warning: cannot read baseline {BASELINE}: {exc})')

    if len(suites) < minimum:
        failures.append(f'suite count {len(suites)} < baseline {minimum}')

    print(f'{agent}: {len(suites)} suites, baseline {minimum}')
    if failures:
        print('FAIL:')
        for failure in failures:
            print(f'  - {failure}')
        return 1
    print('manifest matches audit')
    return 0

if __name__ == '__main__':
    sys.exit(main())
