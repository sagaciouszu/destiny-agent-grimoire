#!/usr/bin/env python3
"""Fetch English captions for the Destiny 2 cutscene archive playlist (30 videos).

Subtitle-only download (no video). Writes archive/data/cutscenes.jsonl:
  slug, title, source_url, video_id, lines: [{speaker, text}]
Speaker is 'Cutscene' until migrate.py attributes unique matches.
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'cutscenes.jsonl')
WORK = '/tmp/opencode/cutscenes'

VIDEOS = [
    ('WAw1g2tHN3s', 'Destiny 2: The Red War All Cutscenes (Season 1)'),
    ('4jtZpmcCM4Y', 'Destiny 2: Curse of Osiris All Cutscenes (Season 2)'),
    ('1BLwUWlOqSE', 'Destiny 2: Warmind All Cutscenes (Season 3)'),
    ('0MDrj33Aqqw', 'Destiny 2: Forsaken All Cutscenes (Season 4)'),
    ('uZEfYvm5wIo', 'Destiny 2: Black Armory All Cutscenes (Season 5)'),
    ('VbLQozwChjc', 'Destiny 2: Season of the Drifter All Cutscenes (Season 6)'),
    ('sxjRgPxp1rE', 'Destiny 2: Season of Opulence All Cutscenes (Season 7)'),
    ('MD0KkJiE920', 'Destiny 2: Shadowkeep All Cutscenes & Season of the Undying (Season 8)'),
    ('hTwIjPV-Es0', 'Destiny 2: Season of Dawn All Cutscenes and Quests (Season 9)'),
    ('9fK8l0HL35g', 'Destiny 2: Season of the Worthy All Cutscenes and Quests (Season 10)'),
    ('WaV-wptySRY', 'Destiny 2: Season of Arrivals All Cutscenes and Lore (Season 11)'),
    ('2mYUkw01JWU', 'Destiny 2 Beyond Light - All Cutscenes, All Quests, Full Movie (Season 12)'),
    ('f2uI3G0rzLc', 'Destiny 2 Season of the Hunt (Season 12) - All Cutscenes, All Quests, Full Movie'),
    ('3emSUJgULwg', 'Destiny 2: Season of the Chosen All Cutscenes (Season 13)'),
    ('1TvqvtWk5sk', 'Destiny 2: Season of the Splicer All Cutscenes (Season 14)'),
    ('fyF3AuIxQbs', 'Destiny 2: Season of the Lost All Cutscenes (Season 15)'),
    ('0U_lB7hlU6g', 'Destiny 2: Witch Queen & Season of the Risen All Cutscenes (Season 16)'),
    ('rnyUi4Xq06w', 'Destiny 2: Season of the Haunted all Cutscenes (Season 17)'),
    ('RYMNFA1E6no', 'Destiny 2: Season of Plunder All Cutscenes (Season 18)'),
    ('zxfMEOn15CI', 'Destiny 2: Season of Seraph All Cutscenes (Season 19)'),
    ('K2Xz-J1XBTo', 'Destiny 2: Lightfall The Movie - All Cutscenes & Dialogue (Season 20)'),
    ('ua-RU3KOkMk', 'Destiny 2: Season of Defiance All Cutscenes & Dialogue (Season 20)'),
    ('CIXVkFoSuVU', 'Destiny 2: Season of the Deep All Cutscenes & Dialogue (Season 21)'),
    ('nb5cVZpUt40', 'Destiny 2: Season of the Witch Movie - All Cutscenes & Dialogue (Season 22)'),
    ('LiMnhflVb84', 'Destiny 2: Season of the Wish Movie - All Cutscenes & Dialogue (Season 23)'),
    ('vRX_fOpe96c', 'Destiny 2: The Final Shape The Movie - All Cutscenes & Dialogue (Season 24)'),
    ('J5XLsdUGmkc', 'Destiny 2: Episode 1 Echoes Movie - All Cutscenes & Dialogue (Season 24)'),
    ('7xamvoVrrYU', 'Destiny 2: Episode 2 Revenant Movie - All Cutscenes & Dialogue (Season 25)'),
    ('t_ECtup2WAY', 'Destiny 2: Episode 3 Heresy Movie - All Cutscenes & Dialogue (Season 26)'),
    ('O6N7h1F92Qs', 'Destiny 1: The Movie (2014-2017) All Cutscenes + DLC'),
    ('8gMDQ4tOyFg', 'Destiny 1 - The Movie (All Cutscenes)'),
    # Rich same-season mirrors (alternates when archive entries are throttled)
    ('0DMzSwZmBcQ', 'Destiny 2: Black Armory All Cutscenes (Season 5) (AKA Season of the Forge)'),
    ('YRYH6WzbMLs', 'DESTINY 2: SEASON OF THE CHOSEN All Cutscenes (Game Movie)'),
    ('DqjABAIn95Y', 'Destiny 2: Season of the Splicer - All Saint 14 Cutscenes & Quest Dialogue'),
    ('T83W6y08Z7M', 'Destiny 2 - Season of the Lost (All Cutscenes & Dialogue)'),
    # Alternate uploads used when the archive-series entry is throttled
]

STAGE = re.compile(r'^\[(music|musical|song|singing|humming|applause|laughter|chuckles|gasps?|crowd|static|interference|whirring|thrumming|beeping|alarm|rain|wind|thunder|explosion|gunfire|footsteps|door|roar|growl|screech|whispering|voices|echo)[^\]]*\]$', re.I)


def slugify(title):
    s = title.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:60].strip('-')


def parse_vtt(path):
    """Parse auto-captions with rolling accumulation into clean lines."""
    raw = open(path, encoding='utf-8', errors='ignore').read()
    raw = re.sub(r'WEBVTT.*?\n\n', '', raw, flags=re.S)
    cues = []
    for block in re.split(r'\n\n+', raw):
        lines = [l for l in block.split('\n') if l.strip()]
        if not lines:
            continue
        if '-->' in lines[0]:
            lines = lines[1:]
        text = ' '.join(lines)
        text = re.sub(r'<[^>]+>', '', text)          # strip inline tags
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            cues.append(text)
    # rolling accumulation: each cue extends the current sentence
    out = []
    buf = ''
    for ct in cues:
        if not buf:
            buf = ct
        elif ct.startswith(buf.rstrip()):
            buf = ct
        elif buf.rstrip().startswith(ct.rstrip()):
            continue
        else:
            out.append(buf.strip())
            buf = ct
    if buf.strip():
        out.append(buf.strip())
    # dedupe consecutive identical lines
    dedup = []
    for l in out:
        if not dedup or dedup[-1] != l:
            dedup.append(l)
    return dedup


def main():
    os.makedirs(WORK, exist_ok=True)
    done = set()
    if os.path.exists(OUT):
        for ln in open(OUT):
            try:
                done.add(json.loads(ln)['video_id'])
            except Exception:
                pass
    only = set(sys.argv[1:])
    todo = [(v, t) for v, t in VIDEOS if v not in done and (not only or v in only)]
    print(f'{len(VIDEOS)} videos, {len(done)} done, {len(todo)} to fetch')
    errs = 0
    with open(OUT, 'a') as f:
        for i, (vid, title) in enumerate(todo, 1):
            vtt = os.path.join(WORK, vid + '.en.vtt')
            if not os.path.exists(vtt):
                url = f'https://www.youtube.com/watch?v={vid}'
                args = ['yt-dlp', '--skip-download', '--write-subs', '--write-auto-subs',
                        '--sub-langs', 'en-orig,en', '--sub-format', 'vtt',
                        '-o', os.path.join(WORK, vid), url]
                if os.environ.get('YT_CLIENT'):
                    args[1:1] = ['--extractor-args', 'youtube:player_client=' + os.environ['YT_CLIENT']]
                r = subprocess.run(args, capture_output=True, text=True, timeout=300)
                if r.returncode != 0:
                    errs += 1
                    print(f'ERR {vid}: {r.stderr.strip()[-200:]}', file=sys.stderr)
                    time.sleep(30)
                    continue
                time.sleep(8)
            if not os.path.exists(vtt):
                errs += 1
                print(f'ERR {vid}: no caption file', file=sys.stderr)
                continue
            lines = parse_vtt(vtt)
            if not lines:
                errs += 1
                print(f'ERR {vid}: empty after parse', file=sys.stderr)
                continue
            rec = {
                'slug': 'cutscene-' + slugify(title),
                'title': title,
                'source_url': f'https://www.youtube.com/watch?v={vid}',
                'video_id': vid,
                'lines': [{'speaker': 'Cutscene', 'text': l} for l in lines],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            f.flush()
            print(f'[{i}/{len(todo)}] {vid}: {len(lines)} lines')
    print(f'done, errors: {errs}')


if __name__ == '__main__':
    main()
