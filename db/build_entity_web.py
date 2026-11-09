#!/usr/bin/env python3
"""Entity web build for the Destiny Grimoire database.

Additive only. Creates entities / entity_aliases / entity_links /
entity_relations / entity_build_meta and the public views v_entity_resolve,
v_entity_documents and v_entity_coverage on a copy of the database. No
existing table, view or row is touched; books/lore/transcripts stay
byte-identical by construction (read-only scan).

    cp db/grimoire.db /tmp/opencode/grimoire-build.db
    python3 db/build_entity_web.py --db /tmp/opencode/grimoire-build.db

Lexicon: high-confidence rows of entity-lexicon-proposal.tsv plus the
owner rulings of 2026-11-09 (see RELEASE.md). Owner-commissioned rows ship
reviewed=1 with their evidence confidence (medium/low) preserved. Aliases
marked requires_ctx match only attribution slots or first sentences.

Usage:
  --db PATH       database to build on (the temp copy, never the live file)
  --tsv PATH      entity lexicon TSV (default: db/entity-lexicon-proposal.tsv)
  --dry-run       load + validate + print the lexicon plan, write nothing
  --report PATH   write a JSON build report
  --skip-scan     create tables/load lexicon, skip the corpus link scan
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import api  # noqa: E402  (fold_name, _fold_key: one shared implementation)

DEFAULT_TSV = os.path.join(HERE, 'entity-lexicon-proposal.tsv')
NEW_SCHEMA_VERSION = '1.6.0'
BUILD_ID = 'entity-web-v0.33.0-2026-11-09'
SRC_NOTE = 'source/lexicon-v1 + owner-rulings-2026-11-09'

DDL = """
CREATE TABLE entities (
    id          INTEGER PRIMARY KEY,
    canonical   TEXT NOT NULL,
    norm_key    TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL CHECK (kind IN ('char','power','faction','place')),
    confidence  TEXT NOT NULL DEFAULT 'high'
                CHECK (confidence IN ('high','medium','low')),
    reviewed    INTEGER NOT NULL DEFAULT 0,
    source      TEXT NOT NULL DEFAULT 'lexicon-v1',
    first_seen  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_entities_kind ON entities(kind);

CREATE TABLE entity_aliases (
    id            INTEGER PRIMARY KEY,
    entity_id     INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    alias         TEXT NOT NULL UNIQUE,
    norm_alias    TEXT NOT NULL UNIQUE,
    weight        REAL NOT NULL DEFAULT 1.0,
    confidence    TEXT NOT NULL DEFAULT 'medium'
                  CHECK (confidence IN ('high','medium','low')),
    requires_ctx  INTEGER NOT NULL DEFAULT 0,
    reviewed      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_entity_aliases_entity ON entity_aliases(entity_id);

CREATE TABLE entity_links (
    id         INTEGER PRIMARY KEY,
    entity_id  INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK (kind IN
                 ('transcript','book','book_entry','lore_entry','item','record','seal')),
    ref        TEXT NOT NULL,
    weight     REAL NOT NULL,
    match      TEXT NOT NULL DEFAULT 'alias'
               CHECK (match IN ('attribution','canonical','alias','ctx_alias','fuzzy')),
    build_id   TEXT NOT NULL,
    UNIQUE (entity_id, kind, ref)
);
CREATE INDEX idx_entity_links_entity ON entity_links(entity_id);
CREATE INDEX idx_entity_links_kind_ref ON entity_links(kind, ref);
CREATE INDEX idx_entity_links_rank ON entity_links(entity_id, weight DESC);

CREATE TABLE entity_relations (
    id              INTEGER PRIMARY KEY,
    entity_id       INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation        TEXT NOT NULL CHECK (relation IN ('adjacent_to','related_to')),
    target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    source          TEXT NOT NULL DEFAULT 'owner-ruling-2026-11-09',
    UNIQUE (entity_id, relation, target_entity_id)
);
CREATE INDEX idx_entity_relations_target ON entity_relations(target_entity_id);

CREATE TABLE entity_build_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE VIEW v_entity_resolve AS
SELECT e.id AS entity_id, e.canonical, e.kind, e.confidence AS entity_confidence,
       a.alias, a.norm_alias, a.confidence AS alias_confidence,
       a.requires_ctx, a.reviewed, e.norm_key
FROM entity_aliases a JOIN entities e ON e.id = a.entity_id;

CREATE VIEW v_entity_documents AS
SELECT l.entity_id, e.canonical, e.kind, l.kind AS doc_kind, l.ref,
       l.weight, l.match,
       ROW_NUMBER() OVER (PARTITION BY l.entity_id
                          ORDER BY l.weight DESC, l.ref) AS rank_in_entity
FROM entity_links l JOIN entities e ON e.id = l.entity_id;

CREATE VIEW v_entity_coverage AS
WITH k AS (
  SELECT e.id, e.kind, COUNT(l.id) AS links, SUM(l.weight) AS weight_sum
  FROM entities e LEFT JOIN entity_links l ON l.entity_id = e.id
  GROUP BY e.id
)
SELECT kind, COUNT(*) AS entities,
       SUM(CASE WHEN links>0 THEN 1 ELSE 0 END) AS entities_with_links,
       SUM(links) AS links, AVG(links) AS avg_links_per_entity
FROM k GROUP BY kind;
"""

DROP_DDL = """
DROP VIEW IF EXISTS v_entity_coverage;
DROP VIEW IF EXISTS v_entity_documents;
DROP VIEW IF EXISTS v_entity_resolve;
DROP TABLE IF EXISTS entity_links;
DROP TABLE IF EXISTS entity_relations;
DROP TABLE IF EXISTS entity_aliases;
DROP TABLE IF EXISTS entity_build_meta;
DROP TABLE IF EXISTS entities;
"""

# Aliases that only count with attribution or first-sentence context (TSV
# 'context rule' marks, plus owner-commissioned parable/noun phrases).
REQUIRES_CTX = {
    'the tower', 'tower', 'mercury',
    'diner', 'pulled pork',
    'gardener', 'the gardener', 'winnower',
}

# Owner rulings of 2026-11-09 encoded verbatim. Everything here ships
# reviewed=1; confidence stays at its evidence grade. Canonical speaker label
# is Elsie Bray (2026-11-09 late flip: was Exo Stranger); Exo Stranger and
# Elisabeth Bray stay aliases of the same entity.
ENTITY_RENAMES = [
    ('char', 'Exo Stranger', 'Elsie Bray'),  # owner flip, rides in v0.33.0
]

OWNER_ALIASES = [
    # (kind, canonical, alias, confidence, requires_ctx, reason)
    ('char', 'Elsie Bray', 'Elsie Bray', 'high', 0, 'owner flip: Elsie Bray is the canonical speaker label and entity canonical; 182+3 transcript_lines rows'),
    ('char', 'Elsie Bray', 'Exo Stranger', 'high', 0, 'owner flip: Exo Stranger remains an alias of the Elsie Bray entity (beyond Light identity)'),
    ('char', 'Elsie Bray', 'Elisabeth Bray', 'high', 0, 'committed speaker fold (v0.32.0, re-anchored to Elsie Bray 2026-11-09); same evidence class'),
    ('char', 'Osiris', 'Reflection of Osiris', 'high', 0, 'owner ruling: Reflection of Osiris folded into Osiris (v0.32.0)'),
    ('power', 'The Traveler', 'great machine', 'medium', 0, 'owner ruling: Great Machine (Eliksni term) = the Traveler'),
    ('power', 'The Traveler', 'the great machine', 'medium', 0, 'owner ruling: Great Machine (Eliksni term) = the Traveler'),
    ('char', 'Glint', 'Diner', 'medium', 1, 'owner ruling: Glint alias; common-noun collision, context rule'),
    ('char', 'Glint', 'Pulled Pork', 'medium', 1, 'owner ruling: Glint alias; common-noun collision, context rule'),
    ('char', 'Clovis Bray', 'Clovis Bray', 'medium', 0, 'owner ruling: Clovis Bray person and AI are ONE entity; corpus speaker label (20 lines)'),
    ('char', 'Clovis Bray', 'Clovis Bray AI', 'medium', 0, 'owner ruling: same entity; hologram voice label (106 lines)'),
    ('char', 'Clovis Bray', 'Clovis Bray I', 'medium', 0, 'owner ruling: same entity (Clovis Bray = Clovis Bray I = Clovis Bray AI)'),
    ('char', 'Siren of Riven', 'Siren of Riven', 'low', 0, 'owner ruling: entity ADJACENT to Riven (creation of her will); relation, not alias; 26 speaker lines'),
    ('power', 'The Worm', 'the worm', 'medium', 0, 'owner ruling: Xol kept as power per proposal; Will of the Thousands'),
    ('power', 'The Worm', 'xol', 'medium', 0, 'owner ruling: Xol = Will of the Thousands = The Worm'),
    ('power', 'The Worm', 'worm god', 'medium', 0, 'owner ruling: Xol kept as power per proposal; attested epithet'),
    ('power', 'The Gardener', 'gardener', 'low', 1, 'owner ruling: Gardener = Light primeval; parable-only, context rule'),
    ('power', 'The Gardener', 'the gardener', 'low', 1, 'owner ruling: Gardener = Light primeval; parable-only, context rule'),
    ('power', 'The Winnower', 'winnower', 'low', 1, 'owner ruling: Winnower = Darkness primeval; parable-only, context rule'),
]

OWNER_ENTITIES = [
    # (kind, canonical, confidence, source)
    ('char', 'Clovis Bray', 'medium', 'owner-ruling-2026-11-09'),
    ('char', 'Siren of Riven', 'low', 'owner-ruling-2026-11-09'),
    ('power', 'The Worm', 'medium', 'owner-ruling-2026-11-09'),
    ('power', 'The Gardener', 'low', 'owner-ruling-2026-11-09'),
    ('power', 'The Winnower', 'low', 'owner-ruling-2026-11-09'),
]

OWNER_RELATIONS = [
    ('The Gardener', 'related_to', 'The Traveler'),
    ('The Winnower', 'related_to', 'The Darkness'),
    ('Siren of Riven', 'adjacent_to', 'Riven'),
    ('SIVA', 'related_to', 'Rasputin'),
]


def log(msg):
    print(msg, flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_lexicon(tsv_path):
    """Return (entities, aliases) from the TSV high rows + owner overlay."""
    entities = {}
    aliases = []
    with open(tsv_path, encoding='utf-8') as fh:
        rows = [line.rstrip('\n').split('\t') for line in fh][1:]
    high = [r for r in rows if len(r) >= 6 and r[4] == 'high']
    log(f'TSV: {len(rows)} rows total, {len(high)} high-confidence rows')
    for kind, canonical, alias, corpus_lines, confidence, reason in high:
        for rkind, old, new in ENTITY_RENAMES:
            if kind == rkind and canonical == old:
                log(f'rename (owner flip): {old} -> {new}')
                canonical = new
                alias = new if alias == old else alias
                break
        key = (kind, canonical)
        entities.setdefault(key, {'confidence': confidence, 'source': 'lexicon-v1'})
        ctx = 1 if api.fold_name(alias) in REQUIRES_CTX else 0
        aliases.append({'kind': kind, 'canonical': canonical, 'alias': alias,
                        'confidence': confidence, 'requires_ctx': ctx,
                        'reviewed': 1, 'source': 'tsv-high'})
    # The corpus was speaker-folded in v0.31/0.32, so several TSV rows are now
    # pure case variants of the same surface form. Folds are stored once per
    # entity; variants collapsing onto the same norm within one entity merge,
    # variants colliding across different entities are fatal.
    by_norm = collections.defaultdict(list)
    for a in aliases:
        by_norm[api.fold_name(a['alias'])].append(a)
    merged = []
    deduped = []
    for norm, group in by_norm.items():
        entity_set = {(a['kind'], a['canonical']) for a in group}
        if len(entity_set) > 1:
            for a in group:
                log(f"ERROR: norm_alias {norm!r} spans entities: {a['alias']!r} ({a['canonical']})")
            raise SystemExit('FATAL: lexicon has cross-entity folded-name collisions')
        keep = next((a for a in group if a['alias'] == a['canonical']), group[0])
        variants = [a['alias'] for a in group if a is not keep]
        if variants:
            merged.append(f'{keep["alias"]!r} <= {variants}')
        deduped.append(keep)
    for m in merged:
        log(f'merged folded alias variants: {m}')
    aliases = deduped
    for kind, canonical, confidence, source in OWNER_ENTITIES:
        key = (kind, canonical)
        if key in entities:
            raise SystemExit(f'FATAL: owner entity collides with TSV entity: {key}')
        entities[key] = {'confidence': confidence, 'source': source}
    for kind, canonical, alias, confidence, ctx, reason in OWNER_ALIASES:
        if (kind, canonical) not in entities:
            raise SystemExit(f'FATAL: owner alias for unknown entity: {kind} {canonical}')
        aliases.append({'kind': kind, 'canonical': canonical, 'alias': alias,
                        'confidence': confidence, 'requires_ctx': ctx,
                        'reviewed': 1, 'source': 'owner-ruling-2026-11-09'})
    # owner overlay can restate a TSV-derived surface form (same entity, same
    # fold): keep one row, prefer the canonical-matching display spelling
    by_norm = collections.defaultdict(list)
    for a in aliases:
        by_norm[(a['kind'], a['canonical'], api.fold_name(a['alias']))].append(a)
    merged = []
    deduped = []
    for key, group in by_norm.items():
        if len(group) == 1:
            deduped.append(group[0])
            continue
        keep = next((a for a in group if api.fold_name(a['alias']) == api._fold_key(a['canonical'])), group[0])
        merged.append(f"{keep['alias']!r} <= {[a['alias'] for a in group if a is not keep]}")
        deduped.append(keep)
    for m in merged:
        log(f'merged duplicate alias (rename residue): {m}')
    return entities, deduped


def validate_lexicon(entities, aliases):
    errors = []
    seen_norm = {}
    for ent in aliases:
        norm = api.fold_name(ent['alias'])
        other = seen_norm.get(norm)
        if other is not None and (other['kind'], other['canonical']) != (ent['kind'], ent['canonical']):
            errors.append(f'norm_alias collision: {ent["alias"]!r} and {other["alias"]!r} both fold to {norm!r} ({other["canonical"]} vs {ent["canonical"]})')
        else:
            seen_norm.setdefault(norm, ent)
    keys = {}
    for (kind, canonical) in entities:
        key = api._fold_key(canonical)
        other = keys.get(key)
        if other is not None:
            errors.append(f'norm_key collision: {canonical!r} and {other!r} both fold to {key!r}')
        else:
            keys[key] = canonical
    if errors:
        for e in errors:
            log('ERROR: ' + e)
        raise SystemExit('FATAL: lexicon validation failed')


def weight_for(alias_row, is_canonical_fold):
    if alias_row['requires_ctx']:
        return 0.75
    if is_canonical_fold:
        return 3.0
    return 1.5


def first_sentence_end(text):
    best = len(text)
    for sep in ('. ', '!', '?', '.\n', '!\n', '?\n'):
        idx = text.find(sep)
        if idx != -1:
            best = min(best, idx + 1)
    return min(best, 240)


def classify_match(matches):
    if any(m.get('attribution') for m in matches):
        return 'attribution'
    if any(m.get('canonical') for m in matches):
        return 'canonical'
    if any(not m.get('ctx') for m in matches):
        return 'alias'
    return 'ctx_alias'


def build_links(conn):
    log('link scan: loading alias table')
    alias_rows = conn.execute(
        "SELECT a.id, a.entity_id, a.alias, a.norm_alias, a.requires_ctx, a.weight, "
        "e.kind, e.norm_key, e.canonical "
        "FROM entity_aliases a JOIN entities e ON e.id = a.entity_id").fetchall()
    by_norm = {a['norm_alias']: dict(a) for a in alias_rows}
    keys = sorted(by_norm, key=len, reverse=True)
    pattern = re.compile(r'(?<![0-9a-z])(' + '|'.join(re.escape(k) for k in keys) + r')(?![0-9a-z])')
    char_norms = {}
    for a in alias_rows:
        if a['kind'] == 'char':
            char_norms.setdefault(a['norm_alias'], []).append(a['entity_id'])

    links = collections.defaultdict(list)  # (entity_id, kind, ref) -> [match]

    def record(entity_id, kind, ref, m):
        links[(entity_id, kind, ref)].append(m)

    def make_match(a, ctx_ok, is_attribution=False):
        if a['requires_ctx']:
            # a context-satisfied alias never outranks a plain canonical match
            canonical = False
            weight = 0.75
        else:
            canonical = a['norm_alias'] == a['norm_key'] or a['norm_alias'] == api.fold_name(a['canonical'])
            weight = 3.0 if canonical else 1.5
        if is_attribution:
            weight = 4.0
        return {'weight': weight, 'ctx': bool(ctx_ok),
                'attribution': bool(is_attribution), 'canonical': bool(canonical),
                'norm': a['norm_alias']}

    timings = {}

    def scan(text, ctx_ok_fn):
        """Yield (alias_row, ctx_ok) for matches in folded raw text."""
        ftext = api.fold_name(text)
        if len(ftext) < 2:
            return
        end = first_sentence_end(ftext)
        for m in pattern.finditer(ftext):
            a = by_norm.get(m.group(0))
            if a is None:
                continue
            if a['requires_ctx']:
                if ctx_ok_fn(m.start(), end):
                    yield a, True
            else:
                yield a, False

    # --- transcript lines (content + char attribution) -----------------------
    t0 = time.time()
    log('link scan: transcript_lines')
    n_lines = 0
    cur = conn.execute(
        'SELECT tl.id, tl.speaker, tl.line, t.slug FROM transcript_lines tl '
        'JOIN transcripts t ON t.id = tl.transcript_id')
    while True:
        batch = cur.fetchmany(5000)
        if not batch:
            break
        for _tl_id, speaker, line, slug in batch:
            n_lines += 1
            fspeaker = api.fold_name(speaker) if speaker else ''
            if fspeaker:
                for eid in char_norms.get(fspeaker, ()):  # attribution slot
                    record(eid, 'transcript', slug,
                           {'weight': 4.0, 'ctx': False, 'attribution': True,
                            'canonical': False, 'norm': fspeaker})
            if not line:
                continue
            for a, ctx_ok in scan(line, lambda pos, end: pos < end):
                record(a['entity_id'], 'transcript', slug, make_match(a, ctx_ok))
    timings['transcripts'] = round(time.time() - t0, 2)
    log(f'  {n_lines} lines scanned in {timings["transcripts"]}s')

    # --- book entries (+ book roll-up) ----------------------------------------
    t0 = time.time()
    log('link scan: book_entries')
    book_rollup = collections.defaultdict(list)
    n = 0
    for be_id, slug, title, body in conn.execute(
            'SELECT be.id, books.slug, be.title, be.body FROM book_entries be '
            'JOIN books ON books.id = be.book_id'):
        n += 1
        text = f'{title or ""} {body or ""}'
        ref = f'book_entries:{be_id}'
        for a, ctx_ok in scan(text, lambda pos, end: pos < end):
            m = make_match(a, ctx_ok)
            record(a['entity_id'], 'book_entry', ref, m)
            book_rollup[slug].append((a['entity_id'], m))
    for slug, entries in book_rollup.items():
        per_entity = collections.defaultdict(list)
        for eid, m in entries:
            per_entity[eid].append(m)
        for eid, mlist in per_entity.items():
            m = dict(max(mlist, key=lambda mm: mm['weight']))
            m['weight'] = round(min(4.0, m['weight'] + 0.5), 3)
            record(eid, 'book', slug, m)
    timings['books'] = round(time.time() - t0, 2)
    log(f'  {n} entries scanned in {timings["books"]}s')

    # --- lore entries (exclude duplicates) -------------------------------------
    t0 = time.time()
    log('link scan: lore_entries (is_duplicate=0)')
    n = skipped = 0
    for lore_hash, title, body in conn.execute(
            'SELECT hash, title, body FROM lore_entries WHERE is_duplicate = 0'):
        n += 1
        text = f'{title or ""} {body or ""}'
        if len(api.fold_name(text)) < 3:
            skipped += 1
            continue
        ref = f'lore_entries:{lore_hash}'
        for a, ctx_ok in scan(text, lambda pos, end: pos < end):
            record(a['entity_id'], 'lore_entry', ref, make_match(a, ctx_ok))
    timings['lore'] = round(time.time() - t0, 2)
    log(f'  {n} entries scanned ({skipped} skipped) in {timings["lore"]}s')

    # --- items (title holds the tokens even when norm_text is empty) -----------
    t0 = time.time()
    log('link scan: items')
    n = 0
    for item_slug, title, text in conn.execute('SELECT slug, title, text FROM items'):
        n += 1
        full = f'{title or ""} {text or ""}'
        if len(api.fold_name(full)) < 3:
            continue
        for a, ctx_ok in scan(full, lambda pos, end: pos < end):
            record(a['entity_id'], 'item', item_slug, make_match(a, ctx_ok))
    timings['items'] = round(time.time() - t0, 2)
    log(f'  {n} items scanned in {timings["items"]}s')

    # --- records ------------------------------------------------------------------
    t0 = time.time()
    log('link scan: records')
    for slug, title, body in conn.execute('SELECT slug, title, body FROM records'):
        text = f'{title or ""} {body or ""}'
        for a, ctx_ok in scan(text, lambda pos, end: pos < end):
            record(a['entity_id'], 'record', slug, make_match(a, ctx_ok))
    timings['records'] = round(time.time() - t0, 2)

    # --- seals --------------------------------------------------------------------
    t0 = time.time()
    log('link scan: seals')
    for seal_hash, name, description in conn.execute('SELECT hash, name, description FROM seals'):
        text = f'{name or ""} {description or ""}'
        for a, ctx_ok in scan(text, lambda pos, end: pos < end):
            record(a['entity_id'], 'seal', f'seals:{seal_hash}', make_match(a, ctx_ok))
    timings['seals'] = round(time.time() - t0, 2)

    # --- aggregate + insert ---------------------------------------------------------
    t0 = time.time()
    log(f'link scan: aggregating {len(links)} (entity, document) pairs')
    rows = []
    for (entity_id, kind, ref), mlist in links.items():
        weight = min(4.0, max(m['weight'] for m in mlist)
                           + 0.25 * (len({m['norm'] for m in mlist}) - 1))
        rows.append((entity_id, kind, ref, round(weight, 3), classify_match(mlist), BUILD_ID))
    conn.executemany(
        'INSERT INTO entity_links (entity_id, kind, ref, weight, match, build_id) '
        'VALUES (?,?,?,?,?,?)', rows)
    conn.commit()
    timings['aggregate'] = round(time.time() - t0, 2)
    log(f'  {len(rows)} links inserted in {timings["aggregate"]}s')
    return timings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--db', required=True)
    ap.add_argument('--tsv', default=DEFAULT_TSV)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report')
    ap.add_argument('--skip-scan', action='store_true')
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    log(f'build target: {db_path}')
    tsv_sha = sha256_file(args.tsv)
    log(f'lexicon TSV sha256: {tsv_sha}')

    entities, aliases = load_lexicon(args.tsv)
    validate_lexicon(entities, aliases)
    log(f'lexicon plan: {len(entities)} entities, {len(aliases)} aliases')
    for (kind, canonical), meta in sorted(entities.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        ent_aliases = [a for a in aliases if a['canonical'] == canonical]
        log(f'  [{kind:7}] {canonical:26} ({meta["confidence"]:6}) [{meta["source"]}] aliases={len(ent_aliases)}')
    if args.dry_run:
        log('dry run: no writes performed')
        return 0

    db_sha = sha256_file(db_path)
    t0 = time.time()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(DROP_DDL)
    conn.executescript(DDL)
    build_start = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

    entity_id = {}
    for (kind, canonical), meta in sorted(entities.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        cur = conn.execute(
            "INSERT INTO entities (canonical, norm_key, kind, confidence, reviewed, source) "
            "VALUES (?,?,?,?,1,?)",
            (canonical, api._fold_key(canonical), kind, meta['confidence'], meta['source']))
        entity_id[(kind, canonical)] = cur.lastrowid

    for a in aliases:
        eid = entity_id[(a['kind'], a['canonical'])]
        norm = api.fold_name(a['alias'])
        is_canonical = norm == api._fold_key(a['canonical']) or norm == api.fold_name(a['canonical'])
        conn.execute(
            'INSERT INTO entity_aliases (entity_id, alias, norm_alias, weight, confidence, requires_ctx, reviewed) '
            'VALUES (?,?,?,?,?,?,1)',
            (eid, a['alias'], norm, weight_for(a, is_canonical), a['confidence'], a['requires_ctx']))

    for src, relation, dst in OWNER_RELATIONS:
        src_id = next(v for k, v in entity_id.items() if k[1] == src)
        dst_id = next(v for k, v in entity_id.items() if k[1] == dst)
        conn.execute(
            'INSERT INTO entity_relations (entity_id, relation, target_entity_id) VALUES (?,?,?)',
            (src_id, relation, dst_id))
    conn.commit()
    n_alias = conn.execute('SELECT COUNT(*) FROM entity_aliases').fetchone()[0]
    log(f'inserted {len(entity_id)} entities, {n_alias} aliases, {len(OWNER_RELATIONS)} relations')

    timings = {}
    if not args.skip_scan:
        timings = build_links(conn)

    # ref integrity: every ref must resolve to exactly one parent row
    checks = [
        ('transcript', "SELECT COUNT(*) FROM entity_links WHERE kind='transcript' AND ref NOT IN (SELECT slug FROM transcripts)"),
        ('book', "SELECT COUNT(*) FROM entity_links WHERE kind='book' AND ref NOT IN (SELECT slug FROM books)"),
        ('book_entry', "SELECT COUNT(*) FROM entity_links WHERE kind='book_entry' AND CAST(substr(ref, length('book_entries:')+1) AS INTEGER) NOT IN (SELECT id FROM book_entries)"),
        ('lore_entry', "SELECT COUNT(*) FROM entity_links WHERE kind='lore_entry' AND CAST(substr(ref, length('lore_entries:')+1) AS INTEGER) NOT IN (SELECT hash FROM lore_entries)"),
        ('item', "SELECT COUNT(*) FROM entity_links WHERE kind='item' AND ref NOT IN (SELECT slug FROM items)"),
        ('record', "SELECT COUNT(*) FROM entity_links WHERE kind='record' AND ref NOT IN (SELECT slug FROM records)"),
        ('seal', "SELECT COUNT(*) FROM entity_links WHERE kind='seal' AND CAST(substr(ref, length('seals:')+1) AS INTEGER) NOT IN (SELECT hash FROM seals)"),
    ]
    for label, sql in checks:
        bad = conn.execute(sql).fetchone()[0]
        if bad:
            raise SystemExit(f'FATAL: {bad} dangling {label} refs; build aborted, nothing swapped')

    link_counts = dict(conn.execute('SELECT kind, COUNT(*) FROM entity_links GROUP BY kind').fetchall())
    match_counts = dict(conn.execute('SELECT match, COUNT(*) FROM entity_links GROUP BY match').fetchall())
    entity_rows = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
    alias_rows = conn.execute('SELECT COUNT(*) FROM entity_aliases').fetchone()[0]
    link_rows = conn.execute('SELECT COUNT(*) FROM entity_links').fetchone()[0]
    relation_rows = conn.execute('SELECT COUNT(*) FROM entity_relations').fetchone()[0]

    # meta: schema version bump + live-count stamps for the new objects
    conn.execute("UPDATE meta SET value=? WHERE key='version'", (NEW_SCHEMA_VERSION,))
    conn.execute("UPDATE meta SET value=? WHERE key='last_updated'",
                 (datetime.datetime.now(datetime.timezone.utc).date().isoformat(),))

    meta = {
        'build_id': BUILD_ID,
        'build_started_utc': build_start,
        'source_db_sha256_prebuild': db_sha,
        'lexicon_tsv_sha256': tsv_sha,
        'lexicon_source': SRC_NOTE,
        'schema_version': NEW_SCHEMA_VERSION,
        'entities': str(entity_rows),
        'entity_aliases': str(alias_rows),
        'entity_links': str(link_rows),
        'entity_relations': str(relation_rows),
        'links_by_kind': json.dumps(link_counts, sort_keys=True),
        'links_by_match': json.dumps(match_counts, sort_keys=True),
        'timings_seconds': json.dumps(timings, sort_keys=True),
        'wall_clock_seconds': str(round(time.time() - t0, 2)),
    }
    for key, value in meta.items():
        conn.execute('INSERT OR REPLACE INTO entity_build_meta (key, value) VALUES (?,?)',
                     (key, str(value)))
    for key, value in [('entities', entity_rows), ('entity_aliases', alias_rows),
                       ('entity_links', link_rows), ('entity_relations', relation_rows),
                       ('entity_build_meta', len(meta))]:
        conn.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)', (key, str(value)))

    conn.execute('ANALYZE')
    conn.commit()
    conn.close()

    report = {
        'build_id': BUILD_ID,
        'entities': entity_rows,
        'aliases': alias_rows,
        'relations': relation_rows,
        'links': link_rows,
        'links_by_kind': link_counts,
        'links_by_match': match_counts,
        'timings_seconds': timings,
        'wall_clock_seconds': round(time.time() - t0, 2),
        'source_db_sha256_prebuild': db_sha,
        'lexicon_tsv_sha256': tsv_sha,
    }
    log(json.dumps(report, indent=2, sort_keys=True))
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
