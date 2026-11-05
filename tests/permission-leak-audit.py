#!/usr/bin/env python3
"""Permission leak audit: deployed agents must deny both peer locations.

For every agent in series/agents.json deployed under OPENCODE_AGENTS (default
~/.config/opencode/agents), assert the primary and -consult entry files deny
read, glob and grep on, for each peer agent: the installed peer directory
(<dest>/<peer>/**) AND the peer's source repo (<Work>/<source>/**). The second
location is where USER.md, journals and memory seeds actually live; without it
the "cross-agent reads are denied" claim leaks.

PASS with a note when OpenCode agents are not deployed on this machine.
Exit 0 pass / 1 fail.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

DEST = os.environ.get('OPENCODE_AGENTS') or os.path.expanduser(
    '~/.config/opencode/agents')
WORK = os.environ.get('AGENT_REPOS_DIR') or os.path.dirname(ROOT)
MANIFEST = os.path.join(ROOT, 'series', 'agents.json')

PASSED = FAILED = 0


def check(name, ok, detail=''):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f'  PASS: {name}')
    else:
        FAILED += 1
        print(f'  FAIL: {name}' + (f' ({detail})' if detail else ''))


def denies(text, action, path):
    pattern = (r'- action: ' + re.escape(action) + r'\s*\n\s*resource: "'
               + re.escape(path) + r'/\*\*"\s*\n\s*effect: deny')
    return re.search(pattern, text) is not None


def main():
    if not os.path.isdir(DEST):
        print('SKIP: OpenCode agents not deployed here '
              f'({DEST} missing) - PASS')
        return 0
    manifest = json.load(open(MANIFEST, encoding='utf-8'))
    agents = manifest.get('agents', [])
    for agent in agents:
        ident = agent.get('id', '')
        for suffix in ('', '-consult'):
            path = os.path.join(DEST, f'{ident}{suffix}.md')
            if not os.path.isfile(path):
                continue  # consult copies only exist after a consult deploy
            text = open(path, encoding='utf-8').read()
            peers = [p for p in agents if p.get('id') != ident]
            for peer in peers:
                peer_id = peer.get('id', '')
                peer_repo = os.path.join(WORK, peer.get('source', ''))
                for action in ('read', 'glob', 'grep'):
                    check(f'{ident}{suffix} denies {action} on installed {peer_id}',
                          denies(text, action, os.path.join(DEST, peer_id)))
                    check(f'{ident}{suffix} denies {action} on repo {peer.get("source")}',
                          denies(text, action, peer_repo))
    print(f'Passed: {PASSED} | Failed: {FAILED}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
