#!/usr/bin/env python3
"""Generate a new series agent from the shared skeleton.

Usage:
    python3 series/new-agent.py example-agent \
        --name "Example Agent" \
        --title "A blank series agent" \
        --dest ../example-agent

The skeleton is intentionally blank: it carries the shared module layout and
audit gates, but no voice, history or relationships from an existing agent.
"""
import argparse
import datetime
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATE = os.path.join(ROOT, 'series', '_template')


def validate_id(value):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', value):
        raise SystemExit('id must be lowercase letters, digits and hyphens')


def render(text, values):
    for key, value in values.items():
        text = text.replace('{{' + key + '}}', value)
    left = re.findall(r'\{\{[a-z0-9_]+\}\}', text)
    if left:
        raise SystemExit(f'unresolved placeholders: {sorted(set(left))}')
    return text


def stamp_tokens(text):
    tokens = max(1, round(len(text) / 4))
    label = f'~{tokens / 1000:.1f}K' if tokens >= 1000 else f'~{tokens} tokens'
    return re.sub(r'Token Estimate:\*\* ~[0-9.]+K? tokens?', f'Token Estimate:** {label}', text, count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('id')
    parser.add_argument('--name', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--emoji', default='✦')
    parser.add_argument('--color', default='#d4af37')
    parser.add_argument('--dest', required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    validate_id(args.id)

    dest = os.path.abspath(os.path.expanduser(args.dest))
    if os.path.exists(dest) and not args.force:
        raise SystemExit(f'destination exists: {dest}')
    if os.path.exists(dest):
        shutil.rmtree(dest)

    values = {
        'id': args.id,
        'name': args.name,
        'name_upper': args.name.upper(),
        'title': args.title,
        'emoji': args.emoji,
        'color': args.color,
        'date': datetime.date.today().isoformat(),
        'minimal': '0.0',
        'standard': '0.0',
        'deep': '0.0',
    }
    renames = {
        'entry.md': f'{args.id}.md',
        'core.md': f'{args.id}-core.md',
        'voice.md': f'{args.id}-voice.md',
        'voice-core.md': f'{args.id}-voice-core.md',
    }

    for root, _dirs, files in os.walk(TEMPLATE):
        rel_root = os.path.relpath(root, TEMPLATE)
        target_root = dest if rel_root == '.' else os.path.join(dest, rel_root)
        os.makedirs(target_root, exist_ok=True)
        for name in files:
            source = os.path.join(root, name)
            target_name = renames.get(name, name)
            target = os.path.join(target_root, target_name)
            with open(source, encoding='utf-8') as f:
                text = f.read()
            if name.endswith(('.md', '.sh', '.py', '.yml', '.json')):
                text = render(text, values)
                if name.endswith('.md'):
                    text = stamp_tokens(text)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(text)
            if name.endswith('.sh') or name.endswith('.py'):
                os.chmod(target, 0o755)

    def size(rel):
        path = os.path.join(dest, rel)
        return len(open(path, encoding='utf-8').read()) / 4 / 1000 if os.path.exists(path) else 0

    core = f'{args.id}-core.md'
    minimal = size(core)
    standard = minimal + size(f'voice/{args.id}-voice-core.md') + size('core/relationships.md')
    deep = 0
    for root, _dirs, files in os.walk(dest):
        for name in files:
            if name.endswith('.md'):
                deep += len(open(os.path.join(root, name), encoding='utf-8').read()) / 4 / 1000
    idx_path = os.path.join(dest, 'INDEX.md')
    idx = open(idx_path, encoding='utf-8').read()
    for tier, value in (('Minimal', minimal), ('Standard', standard), ('Deep', deep)):
        idx = re.sub(rf'(\| {tier} \|[^\n]*?)~[\d.]+K', rf'\g<1>~{value:.1f}K', idx)
    open(idx_path, 'w', encoding='utf-8').write(idx)

    print(f'generated {args.name} ({args.id}) -> {dest}')
    print('next:')
    print('  1. fill the persona sections in the core and voice modules')
    print('  2. add verified lines from the grimoire')
    print('  3. run ./setup.sh && bash tests/master-audit.sh')
    print(f'  4. add the repo and a row to series/agents.json')


if __name__ == '__main__':
    main()
