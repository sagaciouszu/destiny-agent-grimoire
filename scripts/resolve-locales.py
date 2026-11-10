#!/usr/bin/env python3
"""Resolve the English entry indices of an extracted `w64_sr_globals` package.

Input: a directory produced by `tiger-pkg unpack` for one v53 StringBank
package (one `{entry}_{class}_t8_s0.bin` per package entry), e.g.

    python3 scripts/resolve-locales.py \
        /opt/vault/d2-bl-extract/temp/out-w64_sr_globals_0294_0

Output: JSON on stdout (or `--out PATH`) with `english_entries`, the resolved
locale map, and a per-table account of what was accepted, skipped and why.

Why this is not a signature-block rotation
------------------------------------------
`NEXT-PHASE-PROMPT.md` proposed grouping consecutive entries whose pair-run
signature (`tuple(pair.one)`) is identical, anchoring one locale per block,
then rotating the fixed 13-locale cycle.  Measured on package 0294 that
premise is false for the data:

  * 152 of the package's 637 logical tables (23.9%) contain more than one
    distinct pair-run signature.  `sum(pair.one) == nrec`, and `nrec` itself
    varies by locale for 151 tables (a parameter placeholder is present in
    some locales and absent in others), so the signature is *not*
    locale-invariant.  `records[0].x` varies with it.
  * Consequently signature grouping yields 1,345 blocks for 637 real tables:
    617 single-entry fragments, and 8 blocks of 26+ entries where adjacent
    tables with the same signature merge.

Rotating a cycle inside such a block would place English entries on wrong
rows.  This resolver therefore segments with a cycle-constrained dynamic
program over script evidence instead (see "Algorithm" below), and refuses to
emit an entry unless the table it belongs to is *pinned* by at least two
independent script anchors.

Algorithm
---------
1. Parse every `*_t8_s0.bin` entry with a strict reimplementation of
   `/opt/vault/d2-bl-extract/temp/scratch/parse_sb.py` (same structural
   asserts; see `parse_string_bank`).
2. Label each entry by script, using thresholds that the package's own
   verified pass already used (`hardcheck.py`):
       hangul >= 3 -> KO,  kana >= 2 -> JA,  cyrillic >= 8 -> RU,
       CJK >= 2 -> ZH,  no alphabetic char -> NEUTRAL,  else LATIN.
3. Align the whole entry sequence to the fixed locale cycle
       EN, JA, DE, FR, ES, ES-419, IT, KO, ZH-TW, ZH-CN, PT, PL, RU
   with a dynamic program.  Each entry is assigned to the next cycle slot,
   or a slot is skipped (a locale absent from that table).  Hard scripts may
   only land in their own slot: KO->7, RU->12, CJK->8/9, kana->1 (a
   kanji-only Japanese entry is indistinguishable from ZH, so slot 1 accepts
   ZH too).  Latin slots only accept LATIN/NEUTRAL text.  Skipping a slot
   costs 2, so tables naturally stay as long as the evidence allows.
   Index gaps force a table boundary.
4. A table is *verified* only if it carries at least two hard-script anchors
   and at least one of them is in a late slot (>= 6).  Two anchors pin the
   phase uniquely, because each hard label maps to exactly one cycle slot.
   Verified tables that include slot 0 yield their slot-0 entry as English.
   Everything else is reported in `skipped_blocks`; it is never guessed.
5. Two narrow singleton rules, both requiring an actual content signal:
     * a one-entry unverified table is English when its text contains at
       least two distinct unambiguous English function words and no
       competing locale marker (Spanish inverted punctuation, Polish
       diacritics, Portuguese nasal vowels, German umlauts, French
       ligatures, or any non-Latin script);
     * a one-entry unverified table whose text has no alphabetic character
       at all (private-use glyphs, digits, punctuation) is *language
       neutral*; by convention it takes the package default locale, EN.
       Use `--neutral-policy skip` to drop it instead.

Both rules are bucketed separately in the output so a consumer can exclude
them.  On package 0294 the cycle accounts for 632/634, the English singleton
for 1, and the neutral singleton for 1.

Usage
-----
    resolve-locales.py PACKAGE_DIR [--out FILE] [--indices]
                       [--neutral-policy {as-en,skip}]
                       [--class-hash HEX] [--verify MAP]

`--verify` takes either the corpus locale map
(`archive/data/locale-maps/*.json`, key `en_entries`) or the full verified
map (`{"<entry>": "<locale>"}`); it prints a confusion summary and exits 1 on
any false positive.

Pure stdlib, deterministic, no network.
"""
import argparse
import collections
import json
import os
import re
import struct
import sys

FNV1 = 0x811C9DC5
CYCLE = ['EN', 'JA', 'DE', 'FR', 'ES', 'ES-419', 'IT', 'KO', 'ZH-TW',
         'ZH-CN', 'PT', 'PL', 'RU']
CYCLE_INDEX = {loc: i for i, loc in enumerate(CYCLE)}
LATIN_SLOTS = frozenset({0, 2, 3, 4, 5, 6, 10, 11})   # EN DE FR ES ES-419 IT PT PL
CJK_SLOTS = frozenset({8, 9})                          # ZH-TW ZH-CN
HARD_LOCALES = frozenset({'JA', 'KO', 'RU', 'ZH-TW', 'ZH-CN'})

FILE_RE = re.compile(r'^(\d+)_([0-9a-fA-F]+)_t(\d+)_s(\d+)\.bin$')
DEFAULT_CLASS = '808099f1'

SKIP_COST = 2
INF = 10 ** 9

# Unambiguous English function words.  Deliberately excludes forms shared with
# Romance languages ("a", "e", "o", "in", "on", "as", "no").
EN_STOPWORDS = frozenset("""
the and of to you your is are was were for with not this that from will when
can have has had they their there what which would should could into out up
down it its be been by or an does did do if then than them we our us he she
his her him who whom whose all any some more most other such only own same
""".split())

POLISH_MARKERS = frozenset('ąęłńśźżĄĘŁŃŚŹŻ')
PORTUGUESE_MARKERS = frozenset('ãõÃÕ')
GERMAN_MARKERS = frozenset('ßäöüÄÖÜ')
FRENCH_MARKERS = frozenset('œæëïÿŒÆËÏŸ')
SPANISH_MARKERS = frozenset('ñÑ¿¡')

# Function words that are unambiguously non-English, used only to *exclude* a
# lone singleton from the English set (never to assign it a locale).
NON_EN_STOPWORDS = frozenset("""
para sua com uma não você con en la el los las del una che il gli della sono
les des une et est pour vous und der die das nicht mit von zu ist ich du er
sie wir ihr hay muy pero como está este esta todo todos
""".split())


# --------------------------------------------------------------- parser ----


class StringBankError(ValueError):
    """Raised when an entry does not match the verified v53 StringBank layout."""


def parse_string_bank(path):
    """Strict parse of one v53 `t8_s0` StringBank entry.

    Byte-for-byte the same invariants as
    /opt/vault/d2-bl-extract/temp/scratch/parse_sb.py.  Returns the strings in
    record order (`None` for runtime parameter placeholders) plus the pair-run
    signature and header counters used for diagnostics.
    """
    with open(path, 'rb') as fh:
        b = fh.read()

    def u64(o):
        return struct.unpack_from('<Q', b, o)[0]

    def u32(o):
        return struct.unpack_from('<I', b, o)[0]

    def u16(o):
        return struct.unpack_from('<H', b, o)[0]

    file_size = u64(0)
    nrec = u64(0x08)
    f10 = u64(0x10)
    nparam = u64(0x18)
    blob_len = u64(0x28)
    pair_count = u64(0x38)

    if file_size != len(b):
        raise StringBankError('%s: file_size %d != %d' % (path, file_size, len(b)))
    if f10 != 0x40:
        raise StringBankError('%s: header size %#x' % (path, f10))
    if u64(0x50) != nrec:
        raise StringBankError('%s: record count repeat' % path)

    recs = []
    for i in range(nrec):
        o = 0x68 + i * 0x20
        recs.append({
            'idx': i,
            'x': u64(o),
            'marker': u32(o + 0x08),
            'a': u16(o + 0x0C),
            'blen': u16(o + 0x0E),
            't1': u64(o + 0x10),
        })

    off = 0x68 + nrec * 0x20
    if nparam >= 1:
        if u32(off + 4) != 0x80809FB8:
            raise StringBankError('%s: param header' % path)
        if u64(off + 8) != nparam:
            raise StringBankError('%s: param count' % path)
        if u32(off + 0x10) != 0x80809A17:
            raise StringBankError('%s: param magic' % path)
        off += 24 + nparam * 0xC0 + 8

    desc = off
    if u32(desc + 4) != 0x80809FB8:
        raise StringBankError('%s: blob descriptor' % path)
    if u64(desc + 8) != blob_len:
        raise StringBankError('%s: blob length' % path)
    if u32(desc + 0x10) != 0x80800005:
        raise StringBankError('%s: blob magic' % path)
    blob_start = desc + 24
    if u64(0x30) != blob_start - 0x40:
        raise StringBankError('%s: blob offset' % path)
    blob = b[blob_start:blob_start + blob_len]
    if not blob or blob[-1] != 0:
        raise StringBankError('%s: blob terminator' % path)

    cur = 0
    strings = []
    for r in recs:
        if r['marker'] == FNV1:
            raw = blob[cur:cur + r['a']]
            cur += r['a']
            strings.append(raw.decode('utf-8', 'replace'))
        else:
            strings.append(None)
    if cur != blob_len - 1:
        raise StringBankError('%s: blob consumption %d != %d' % (path, cur, blob_len - 1))

    pairs_off = len(b) - pair_count * 16
    if u64(0x40) != pairs_off - 0x50:
        raise StringBankError('%s: pair offset' % path)
    ones = []
    for i in range(pair_count):
        o = pairs_off + i * 16
        ones.append(struct.unpack_from('<Q', b, o + 8)[0])
    if sum(ones) != nrec:
        raise StringBankError('%s: pair sum %d != nrec %d' % (path, sum(ones), nrec))

    return {
        'path': path,
        'nrec': nrec,
        'nparam': nparam,
        'pair_count': pair_count,
        'strings': strings,
        'signature': tuple(ones),
        'x0': recs[0]['x'] if recs else None,
    }


# ------------------------------------------------------------- evidence ----


def script_label(text):
    """Return KO/JA/RU/ZH/NEUTRAL/LATIN for one entry's concatenated strings."""
    hangul = kana = cyrillic = cjk = letters = 0
    for ch in text:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F:
            hangul += 1
        if 0x3040 <= o <= 0x309F or 0x30A0 <= o <= 0x30FF:
            kana += 1
        if 0x0400 <= o <= 0x04FF:
            cyrillic += 1
        if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF:
            cjk += 1
        if ch.isalpha():
            letters += 1
    if hangul >= 3:
        return 'KO'
    if kana >= 2:
        return 'JA'
    if cyrillic >= 8:
        return 'RU'
    if cjk >= 2:
        return 'ZH'
    if letters == 0:
        return 'NEUTRAL'
    return 'LATIN'


def slot_accepts(slot, label):
    """Can an entry with `label` occupy cycle slot `slot`?"""
    if label == 'NEUTRAL':
        return True
    if slot in LATIN_SLOTS:
        return label == 'LATIN'
    if slot == 1:                       # JA; kanji-only JA is labelled ZH
        return label in ('JA', 'ZH')
    if slot == 7:                       # KO
        return label == 'KO'
    if slot in CJK_SLOTS:               # ZH-TW / ZH-CN
        return label == 'ZH'
    if slot == 12:                      # RU
        return label == 'RU'
    return False


def foreign_marker(text):
    """Return a locale name if the text carries an unambiguous non-EN marker."""
    for ch in text:
        o = ord(ch)
        if ch in SPANISH_MARKERS:
            return 'ES'
        if ch in POLISH_MARKERS:
            return 'PL'
        if ch in PORTUGUESE_MARKERS:
            return 'PT'
        if ch in GERMAN_MARKERS:
            return 'DE'
        if ch in FRENCH_MARKERS:
            return 'FR'
        if 0x0400 <= o <= 0x04FF:
            return 'RU'
        if 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF:
            return 'KO'
        if 0x3040 <= o <= 0x30FF:
            return 'JA'
        if 0x3400 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF:
            return 'ZH'
    return None


def english_evidence(text):
    """(distinct English function words, alpha tokens) for a singleton test."""
    tokens = re.findall(r'[A-Za-z]+', text.lower())
    hits = [t for t in tokens if t in EN_STOPWORDS]
    return len(set(hits)), len(tokens)


def non_english_evidence(text):
    """Distinct non-English function words present in a lone singleton."""
    tokens = re.findall(r'[A-Za-z]+', text.lower())
    return len({t for t in tokens if t in NON_EN_STOPWORDS})


def is_glyph_table(text):
    """True when the text is dominated by private-use icon glyphs.

    Icon-glyph tables carry no natural language.  A trailing bracketed
    developer label (e.g. "[Shield Throw]") must not turn one into English.
    """
    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return True
    private_use = sum(1 for c in non_space if 0xE000 <= ord(c) <= 0xF8FF)
    return private_use / len(non_space) >= 0.8


# ---------------------------------------------------------------- align ----


def _align_segment(labels):
    """Cycle-align one gap-free run of entries.  Returns [(entry_pos, slot)]."""
    n = len(labels)
    dp = [[INF] * 13 for _ in range(n + 1)]
    back = [[None] * 13 for _ in range(n + 1)]
    dp[0][0] = 0

    def improve(i, p, cost, prev):
        if cost < dp[i][p]:
            dp[i][p] = cost
            back[i][p] = prev

    for i in range(n + 1):
        # Skips and early closes can revisit slot 0, so relax a few times.
        for _ in range(3):
            for p in range(12):
                if dp[i][p] < INF:
                    improve(i, p + 1, dp[i][p] + SKIP_COST, (i, p, 'skip'))
            for p in range(1, 13):
                if dp[i][p] < INF:
                    improve(i, 0, dp[i][p] + SKIP_COST * (13 - p), (i, p, 'close'))
        if i < n:
            for p in range(13):
                if dp[i][p] < INF and slot_accepts(p, labels[i]):
                    improve(i + 1, (p + 1) % 13, dp[i][p], (i, p, 'assign'))

    end_cost, end_slot = min(
        (dp[n][p] + (SKIP_COST * (13 - p) if p > 0 else 0), p) for p in range(13))

    i, j = n, end_slot
    transitions = []
    if j > 0:
        transitions.append((n, j, 'close'))
    while (i, j) != (0, 0):
        prev = back[i][j]
        if prev is None:
            raise AssertionError('cycle DP backpointer broken at %d,%d' % (i, j))
        transitions.append(prev)
        i, j = prev[0], prev[1]
    transitions.reverse()

    tables = []
    current = []
    for _pi, slot, op in transitions:
        if op == 'assign':
            current.append((_pi, slot))
            if slot == 12:
                tables.append(current)
                current = []
        elif op == 'close' and current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables, end_cost


def align_entries(entries):
    """Align all contiguous runs; return (tables, total_skip_cost)."""
    tables = []
    cost = 0
    run = []
    previous = None
    for entry in entries:
        if previous is not None and entry['index'] != previous + 1:
            if run:
                seg_tables, seg_cost = _align_segment([e['label'] for e in run])
                tables.extend([[(run[p], s) for p, s in t] for t in seg_tables])
                cost += seg_cost
                run = []
        run.append(entry)
        previous = entry['index']
    if run:
        seg_tables, seg_cost = _align_segment([e['label'] for e in run])
        tables.extend([[(run[p], s) for p, s in t] for t in seg_tables])
        cost += seg_cost
    return tables, cost


# ------------------------------------------------------------- resolver ----


def resolve(package_dir, class_hash=DEFAULT_CLASS, neutral_policy='as-en'):
    files = collections.defaultdict(list)
    others = []
    for name in sorted(os.listdir(package_dir)):
        m = FILE_RE.match(name)
        if not m:
            continue
        index, cls, ftype, subtype = m.groups()
        if cls.lower() != class_hash.lower() or ftype != '8' or subtype != '0':
            others.append(name)
            continue
        files[int(index)].append(name)

    entries = []
    parse_failures = []
    duplicates = []
    for index in sorted(files):
        names = files[index]
        if len(names) > 1:
            duplicates.append(index)
        path = os.path.join(package_dir, names[0])
        try:
            parsed = parse_string_bank(path)
        except (StringBankError, struct.error, OSError) as exc:
            parse_failures.append({'entry': index, 'error': str(exc)})
            continue
        text = ' '.join(s for s in parsed['strings'] if s is not None)
        entry = {
            'index': index,
            'path': path,
            'text': text,
            'label': script_label(text),
            'nrec': parsed['nrec'],
            'nparam': parsed['nparam'],
            'signature': parsed['signature'],
            'x0': parsed['x0'],
            'empty': not text.strip(),
        }
        entries.append(entry)

    tables, skip_cost = align_entries(entries)

    english = []
    locale_map = {}
    buckets = collections.Counter()
    skipped = []
    rejected = []
    verified_tables = 0

    for table in tables:
        hard = [(e, s, e['label']) for e, s in table
                if e['label'] in ('KO', 'JA', 'RU', 'ZH')]
        pinned = len(hard) >= 2 and any(s >= 6 for _e, s, _l in hard)

        if pinned:
            verified_tables += 1
            slots = [s for _e, s in table]
            full_cycle = (len(table) == 13 and slots == list(range(13)))
            for entry, slot in table:
                locale = CYCLE[slot]
                # A partial table that lost a Latin-script locale leaves its
                # Latin neighbours ambiguous (the skip can sit on either side
                # of an all-Latin run).  Only claim EN and hard-script slots
                # there; full 13-member tables are exact by construction.
                if full_cycle or locale == 'EN' or locale in HARD_LOCALES:
                    locale_map[entry['index']] = locale
                else:
                    locale_map[entry['index']] = 'LATIN'
            first = [e for e, s in table if s == 0]
            if first:
                english.append(first[0]['index'])
                buckets['cycle'] += 1
            continue

        # Unverified: only narrow, content-driven rules may speak.
        if len(table) == 1:
            entry = table[0][0]
            if entry['empty'] or is_glyph_table(entry['text']):
                if neutral_policy == 'as-en':
                    english.append(entry['index'])
                    locale_map[entry['index']] = 'EN'
                    buckets['neutral-default'] += 1
                    continue
                skipped.append({
                    'first_entry': entry['index'],
                    'size': 1,
                    'reason': 'language-neutral icon-glyph table (policy=skip)',
                })
                continue
            marker = foreign_marker(entry['text'])
            distinct, tokens = english_evidence(entry['text'])
            if marker is None and distinct >= 2 and tokens >= 3:
                english.append(entry['index'])
                locale_map[entry['index']] = 'EN'
                buckets['singleton-en'] += 1
                continue
            non_en = non_english_evidence(entry['text'])
            reason = ('singleton, no cycle anchor; marker=%s, '
                      'english-words=%d/%d, non-english-words=%d'
                      % (marker, distinct, tokens, non_en))
            if marker is not None or non_en >= 1:
                rejected.append({
                    'first_entry': entry['index'],
                    'size': 1,
                    'reason': reason,
                })
            else:
                skipped.append({
                    'first_entry': entry['index'],
                    'size': 1,
                    'reason': reason,
                })
            continue

        skipped.append({
            'first_entry': table[0][0]['index'],
            'last_entry': table[-1][0]['index'],
            'size': len(table),
            'hard_anchors': [[e['index'], s, l] for e, s, l in hard],
            'reason': ('block has %d hard-script anchor(s)'
                       % len(hard)
                       if len(hard) < 2 else
                       'block has no late hard-script anchor (slot >= 6)'),
        })

    english.sort()
    total_tables = len(tables)
    coverage = (verified_tables / total_tables) if total_tables else 0.0
    if coverage >= 0.98 and not skipped:
        confidence = 'high'
    elif coverage >= 0.80:
        confidence = 'medium'
    else:
        confidence = 'low'

    result = {
        'schema': 1,
        'generator': 'scripts/resolve-locales.py',
        'package_dir': package_dir,
        'class_hash': class_hash,
        'cycle': CYCLE,
        'entries_discovered': len(files),
        'entries_parsed': len(entries),
        'entries_other_class_or_type': len(others),
        'parse_failures': parse_failures,
        'duplicate_indices': duplicates,
        'tables_detected': total_tables,
        'tables_verified': verified_tables,
        'table_size_histogram': dict(sorted(
            collections.Counter(len(t) for t in tables).items())),
        'table_coverage': round(coverage, 4),
        'alignment_skip_cost': skip_cost,
        'english_entries': english,
        'en_entries': english,          # alias matching archive locale-map shape
        'english_count': len(english),
        'english_source_buckets': dict(sorted(buckets.items())),
        'latin_ambiguous_entries': sum(1 for v in locale_map.values()
                                       if v == 'LATIN'),
        'skipped_blocks': skipped,
        'rejected_non_english': rejected,
        'confidence': confidence,
        'locale_map': {str(k): locale_map[k] for k in sorted(locale_map)},
        'notes': [
            'Locale is carried by entry position, not by an in-file field.',
            'A table is emitted only when pinned by >=2 hard-script anchors, '
            'at least one in a late slot; unanchored blocks are skipped.',
            'locale_map values other than LATIN are exact for full 13-member '
            'tables, for EN, and for the hard-script locales.  LATIN marks a '
            'Latin-script slot whose sibling locale cannot be separated in a '
            'partial table; it is deliberately not guessed.',
            'Entries listed in rejected_non_english and skipped_blocks are '
            'absent from locale_map.',
        ],
    }
    return result


# ------------------------------------------------------------------ main ----


def load_expected(path):
    """Load an expected EN set from either locale-map shape."""
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    if isinstance(data, dict) and 'en_entries' in data:
        return set(int(x) for x in data['en_entries'])
    if isinstance(data, dict):
        return set(int(k) for k, v in data.items() if v == 'EN')
    raise ValueError('unrecognised expected-map shape: %s' % path)


def verify(result, expected_path):
    expected = load_expected(expected_path)
    got = set(result['english_entries'])
    fp = sorted(got - expected)
    fn = sorted(expected - got)
    print('verify: expected=%d got=%d true_positive=%d false_positive=%d '
          'false_negative=%d' % (len(expected), len(got), len(got & expected),
                                 len(fp), len(fn)), file=sys.stderr)
    if fp:
        print('FALSE POSITIVES (first 40): %s' % fp[:40], file=sys.stderr)
    if fn:
        print('FALSE NEGATIVES (first 40): %s' % fn[:40], file=sys.stderr)
    return fp, fn


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Resolve English entry indices for an extracted '
                    'w64_sr_globals StringBank package.')
    ap.add_argument('package_dir', help='directory of extracted t8_s0 .bin files')
    ap.add_argument('--out', help='write the JSON report here (default: stdout)')
    ap.add_argument('--indices', action='store_true',
                    help='print only the English entry indices, one per line')
    ap.add_argument('--neutral-policy', choices=('as-en', 'skip'), default='as-en',
                    help='treatment of glyph-only language-neutral singletons '
                         '(default: as-en)')
    ap.add_argument('--class-hash', default=DEFAULT_CLASS,
                    help='def class hash to resolve (default: %(default)s)')
    ap.add_argument('--verify', metavar='MAP',
                    help='compare against a verified locale map; exits 1 on any '
                         'false positive')
    args = ap.parse_args(argv)

    if not os.path.isdir(args.package_dir):
        ap.error('not a directory: %s' % args.package_dir)

    result = resolve(args.package_dir, class_hash=args.class_hash,
                     neutral_policy=args.neutral_policy)

    failed = False
    if args.verify:
        fp, _fn = verify(result, args.verify)
        failed = bool(fp)

    if args.indices:
        for index in result['english_entries']:
            print(index)
    else:
        payload = json.dumps(result, indent=2, sort_keys=False)
        if args.out:
            with open(args.out, 'w', encoding='utf-8') as fh:
                fh.write(payload + '\n')
            print('wrote %s (%d English entries, %d/%d tables verified, '
                  'confidence=%s)' % (args.out, result['english_count'],
                                      result['tables_verified'],
                                      result['tables_detected'],
                                      result['confidence']))
        else:
            print(payload)

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
