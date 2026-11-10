#!/usr/bin/env python3
"""Generate or check the canon snapshot in each agent's knowledge web.

The hand-authored part of `reference/knowledge-web.md` stays untouched. This
script owns one managed block sourced from `db/grimoire.db`, so the web cannot
drift from the persona's actual canon.

Usage:
    python3 scripts/generate-knowledge-web.py --check
    python3 scripts/generate-knowledge-web.py --apply
"""
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import _roster  # noqa: E402

DB = os.environ.get('GRIMOIRE_DB') or os.path.join(ROOT, 'db', 'grimoire.db')
BEGIN = '<!-- knowledge-web:begin -->'
END = '<!-- knowledge-web:end -->'
CANON = ("tl.is_stage_dir=0 AND tl.is_optional=0 "
         "AND COALESCE(t.source_tier, '') != 'game_caption'")


def rows(conn, sql, *args):
    return conn.execute(sql, args).fetchall()


def pairs(values):
    return ', '.join(f'{name} ({count})' for name, count in values) or 'none'


def snapshot(conn, speaker):
    canon = rows(
        conn,
        'SELECT COUNT(*) FROM transcript_lines tl '
        'JOIN transcripts t ON t.id=tl.transcript_id '
        f'WHERE tl.speaker=? AND {CANON}', speaker)[0][0]
    transcripts = rows(
        conn,
        'SELECT COUNT(DISTINCT t.id) FROM transcript_lines tl '
        'JOIN transcripts t ON t.id=tl.transcript_id '
        f'WHERE tl.speaker=? AND {CANON}', speaker)[0][0]
    activities = rows(
        conn,
        'SELECT c.activity_slug, COUNT(*) FROM transcript_lines tl '
        'JOIN transcripts t ON t.id=tl.transcript_id '
        'JOIN transcript_classification c ON c.transcript_id=t.id '
        f'WHERE tl.speaker=? AND {CANON} AND c.activity_slug IS NOT NULL '
        'GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 5', speaker)
    seasons = rows(
        conn,
        'SELECT c.season_slug, COUNT(*) FROM transcript_lines tl '
        'JOIN transcripts t ON t.id=tl.transcript_id '
        'JOIN transcript_classification c ON c.transcript_id=t.id '
        f'WHERE tl.speaker=? AND {CANON} AND c.season_slug IS NOT NULL '
        'GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 5', speaker)
    chapters = rows(
        conn,
        'SELECT t.timeline, COUNT(*) FROM transcript_lines tl '
        'JOIN transcripts t ON t.id=tl.transcript_id '
        f'WHERE tl.speaker=? AND {CANON} AND t.timeline IS NOT NULL '
        'GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 5', speaker)
    tiers = rows(
        conn,
        'SELECT COALESCE(t.source_tier, "unknown"), COUNT(*) '
        'FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id '
        f'WHERE tl.speaker=? AND {CANON} GROUP BY 1 ORDER BY 2 DESC, 1', speaker)
    near = rows(
        conn,
        'SELECT other.speaker, COUNT(*) FROM transcript_lines mine '
        'JOIN transcripts t ON t.id=mine.transcript_id '
        'JOIN transcript_lines other ON other.transcript_id=mine.transcript_id '
        'AND ABS(other.seq-mine.seq) <= 3 AND other.speaker != mine.speaker '
        'AND other.is_stage_dir=0 AND other.is_optional=0 '
        "AND other.speaker IS NOT NULL "
        "AND other.speaker NOT IN ('Cutscene','Narration') " 
        f'WHERE mine.speaker=? AND mine.is_stage_dir=0 AND mine.is_optional=0 '
        f'AND COALESCE(t.source_tier, "") != "game_caption" '
        'GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 6', speaker)
    return f'''{BEGIN}
## Canon snapshot (generated)

> Generated from `db/grimoire.db` by `scripts/generate-knowledge-web.py`.
> Do not hand-edit this block; run the script with `--apply`.

| Measure | Value |
|---|---|
| Canonical lines | {canon} |
| Transcripts | {transcripts} |
| Activities | {pairs(activities)} |
| Seasons | {pairs(seasons)} |
| Story chapters | {pairs(chapters)} |
| Source tiers | {pairs(tiers)} |
| Frequent co-speakers | {pairs(near)} |
{END}'''


def managed(text, block):
    if BEGIN in text and END in text:
        before = text.split(BEGIN, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        return before + '\n\n' + block + ('\n\n' + after if after else '\n')
    return text.rstrip() + '\n\n' + block + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not os.path.isfile(DB):
        print(f'FAIL: database missing at {DB}')
        return 1
    conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    issues, changed = [], 0
    try:
        for ident, repo in sorted(_roster.present().items()):
            path = os.path.join(repo, 'reference', 'knowledge-web.md')
            persona = os.path.join(repo, 'persona.json')
            if not os.path.isfile(path) or not os.path.isfile(persona):
                issues.append(f'{ident}: missing knowledge-web.md or persona.json')
                continue
            speaker = json.load(open(persona, encoding='utf-8')).get('speaker')
            if not speaker:
                issues.append(f'{ident}: persona.json has no speaker')
                continue
            block = snapshot(conn, speaker)
            text = open(path, encoding='utf-8').read()
            updated = managed(text, block)
            if updated != text:
                changed += 1
                if args.apply:
                    open(path, 'w', encoding='utf-8').write(updated)
                else:
                    issues.append(f'{ident}: knowledge-web snapshot is stale')
    finally:
        conn.close()
    if args.apply:
        print(f'knowledge webs updated: {changed}')
        return 0
    if issues:
        for issue in issues:
            print(f'  {issue}')
        print(f'FAIL: {len(issues)} knowledge web issue(s); run --apply')
        return 1
    print(f'knowledge webs current: {len(_roster.present())}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
