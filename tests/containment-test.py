#!/usr/bin/env python3
"""Tests for scripts/containment.py.

Self-contained: fixtures live in memory (plus a temporary JSONL file), so no
network, database or corpus data is touched.

Run: python3 tests/containment-test.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import containment  # noqa: E402
from containment import ContainmentIndex, normalise  # noqa: E402

PASS = FAIL = 0

KNOWN = [
    'The Darkness has no shape. It is a tide that rises and falls.',
    'The Vanguard will hold the line until the last light fades from the sky.',
    'Kill Clip reloads the weapon after a kill.',
    'The Antaeus Wards reflect projectiles while sliding today.',
]


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f'  \u2713 {name}')
        PASS += 1
    except Exception as e:
        print(f'  \u2717 {name}: {e}')
        FAIL += 1


def build():
    index = ContainmentIndex()
    for text in KNOWN:
        index.add_text(text, source='fixture')
    return index.finalise()


INDEX = build()


# ------------------------------------------------------------------ cases ----

def exact_match():
    hit = INDEX.match('THE DARKNESS HAS NO SHAPE \u2014 IT IS A TIDE THAT RISES AND FALLS!')
    assert hit is not None, 'exact normalised line should match'
    assert hit.kind == 'exact', f'kind={hit.kind}'
    assert hit.ratio == 1.0 and hit.coverage == 1.0
    assert INDEX.is_fragment(KNOWN[0])


def fragment_match():
    hit = INDEX.match('It is a tide that rises and falls')
    assert hit is not None, '8-token substring should match'
    assert hit.kind == 'substring', f'kind={hit.kind}'
    assert hit.known == normalise(KNOWN[0])
    assert hit.coverage == 1.0


def near_fragment():
    candidate = ('Vanguard shall hold the line until the last light fades '
                 'from the sky')
    hit = INDEX.match(candidate)
    assert hit is not None, 'one-token edit should match as a near-fragment'
    assert hit.kind == 'overlap', f'kind={hit.kind}'
    assert 0.9 <= hit.coverage <= 1.0
    assert 0.9 <= hit.ratio <= 1.0


def short_candidate_guard():
    # 2 tokens / 8 chars: a substring, but far too short to call a fragment.
    assert not INDEX.is_fragment('Kill Clip'), 'short label must not match'
    # 6 tokens / 32 chars: substring, still under the 8-token / 40-char guard.
    assert not INDEX.is_fragment('reloads the weapon after a kill'), \
        'short substring must not match'
    # Same text as a short known entry: the guard applies to exact hits too.
    tiny = ContainmentIndex()
    tiny.add_text('Kill Clip', source='fixture')
    tiny.finalise()
    assert not tiny.is_fragment('Kill Clip'), 'short exact hit must not match'


def long_substring_without_tokens():
    # 6 tokens but 46 characters: the OR clause must let it through.
    candidate = 'Antaeus Wards reflect projectiles while sliding'
    assert len(candidate.split()) < 8 and len(candidate) >= 40
    hit = INDEX.match(candidate)
    assert hit is not None, '>=40-char substring must match despite few tokens'
    assert hit.kind == 'substring', f'kind={hit.kind}'


def normalisation_case():
    a = normalise('It\u2019s the Traveler\u2019s light\u2014and hope\u2026')
    b = normalise("It's the Traveler's light - and hope...")
    assert a == b, (a, b)
    assert a == 'it s the traveler s light and hope', a
    # punctuation-only lines stay non-empty (mirrors migrate.norm_text)
    assert normalise(':)') == ':)'
    assert normalise('') == ''


def threshold_behaviour():
    candidate = ('Vanguard shall hold the line until the last light fades '
                 'from the sky')
    assert INDEX.match(candidate, threshold=0.9) is not None
    assert INDEX.match(candidate, threshold=0.95) is None, \
        'coverage 0.909 must fail a 0.95 threshold'
    assert INDEX.is_fragment(candidate, threshold=0.85)


def unrelated_line():
    assert not INDEX.is_fragment(
        'The Witness watches from the edge of the deep.'), 'unrelated line matched'


def jsonl_loading():
    flat = {'kind': 'item', 'slug': 'item-1',
            'text': 'The Darkness has no shape. It is a tide that rises and falls.'}
    transcript = {'kind': 'caption', 'slug': 'caption-1',
                  'lines': [{'text': 'We need more intel. See what you can uncover.',
                             'hash': 'abc'}]}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'items.jsonl')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(flat) + '\n')
            fh.write(json.dumps(transcript) + '\n')
        index = ContainmentIndex.from_jsonl(path)
        assert index.size == 2, index.size
        assert index.is_fragment(
            'It is a tide that rises and falls'), 'flat record not indexed'
        hit = index.match('We need more intel. See what you can uncover.')
        assert hit is not None and hit.kind == 'exact', hit
        assert hit.ref == 'abc', hit.ref
        assert index.indexed_by_source() == {path: 2}


def cli_stats():
    lines = ['It is a tide that rises and falls',
             'Kill Clip',
             'Nothing in this line resembles the corpus at all.']
    with tempfile.TemporaryDirectory() as tmp:
        items = os.path.join(tmp, 'items.jsonl')
        candidates = os.path.join(tmp, 'lines.txt')
        dump = os.path.join(tmp, 'matches.jsonl')
        with open(items, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps({'text': KNOWN[0], 'slug': 'a'}) + '\n')
        with open(candidates, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = containment.main(['--jsonl', items, '--lines', candidates,
                                   '--dump-matches', dump, '--quiet'])
        assert rc == 0
        stats = json.loads(out.getvalue())
        assert stats['total'] == 3, stats
        assert stats['matched'] == 1, stats
        assert stats['unmatched'] == 2, stats
        assert stats['by_kind']['substring'] == 1, stats
        assert stats['by_source'][items] == 1, stats
        with open(dump, encoding='utf-8') as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        assert len(rows) == 1 and rows[0]['kind'] == 'substring', rows


def determinism():
    candidates = KNOWN + ['It is a tide that rises and falls']
    first = [INDEX.match(c).as_dict() if INDEX.match(c) else None
             for c in candidates]
    second = [INDEX.match(c).as_dict() if INDEX.match(c) else None
              for c in candidates]
    assert first == second


print('containment tests')
check('exact match', exact_match)
check('fragment match', fragment_match)
check('near-fragment', near_fragment)
check('short-candidate guard', short_candidate_guard)
check('long substring with few tokens', long_substring_without_tokens)
check('normalisation (curly quotes / em dash)', normalisation_case)
check('threshold behaviour', threshold_behaviour)
check('unrelated line rejected', unrelated_line)
check('JSONL loading (items + transcript shapes)', jsonl_loading)
check('CLI stats + match dump', cli_stats)
check('deterministic results', determinism)

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
