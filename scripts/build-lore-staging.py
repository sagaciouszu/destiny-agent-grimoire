#!/usr/bin/env python3
"""Flatten DestinyLoreDefinition.json into a local staging JSONL.

Output stays in archive/data/manifest/ (gitignored). Each record carries the
lore hash, title, subtitle, body and the item names that link to it.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, 'archive', 'data', 'manifest')
OUT = os.path.join(MAN, 'lore_entries.jsonl')


def main():
    lore = json.load(open(os.path.join(MAN, 'DestinyLoreDefinition.json'), encoding='utf-8'))
    items = json.load(open(os.path.join(MAN, 'DestinyInventoryItemDefinition.json'), encoding='utf-8'))
    by_hash = {}
    for item in items.values():
        lh = item.get('loreHash')
        if not lh:
            continue
        name = (item.get('displayProperties') or {}).get('name')
        if name:
            by_hash.setdefault(lh, []).append(name)
    count = 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        for key, d in lore.items():
            body = (d.get('displayProperties') or {}).get('description') or ''
            if not body.strip():
                continue
            rec = {
                'hash': int(d.get('hash', key)),
                'title': (d.get('displayProperties') or {}).get('name') or '',
                'subtitle': d.get('subtitle') or '',
                'body': body,
                'item_titles': sorted(set(by_hash.get(int(d.get('hash', key)), []))),
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            count += 1
    print(f'wrote {count} lore entries -> {OUT}')


if __name__ == '__main__':
    main()
