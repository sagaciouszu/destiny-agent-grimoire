#!/usr/bin/env python3
"""Migrate markdown + JSONL sources into SQLite database."""
import os, re, json, glob, sqlite3, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy  # noqa: E402
SCHEMA_VERSION = taxonomy.SCHEMA_VERSION
DB_PATH = os.environ.get('GRIMOIRE_DB') or os.path.join(ROOT, 'db', 'grimoire.db')
SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

def parse_md_sections(path):
    """Parse a book/transcript markdown file into (title, sections, lines)."""
    text = open(path, encoding='utf-8', errors='ignore').read()
    lines = text.split('\n')
    title = lines[0].lstrip('# ').strip() if lines else ''
    sections = []
    cur_title = None
    cur_body = []
    for ln in lines[1:]:
        if ln.startswith('## '):
            if cur_title is not None:
                sections.append((cur_title, '\n'.join(cur_body).strip()))
            cur_title = ln[3:].strip()
            cur_body = []
        elif cur_title is not None:
            cur_body.append(ln)
    if cur_title is not None:
        sections.append((cur_title, '\n'.join(cur_body).strip()))
    return title, sections, lines

# Canonical speaker names: alias variants -> canonical form (STANDARDS.md).
# Contextual qualifiers ("Drifter (Tape 1)", "Eris Morn (communion)") are kept:
# they carry real media/scene meaning and LIKE queries still match the base name.
SPEAKER_ALIASES = {
    'Commander Zavala': 'Zavala',
    'Cayde': 'Cayde-6',
    'Eris': 'Eris Morn',
    'Eris morn': 'Eris Morn',
    'Ikora Rey': 'Ikora',
    'Chiomi Esi': 'Chioma Esi',
    'Queen Mara Sov': 'Mara Sov',
    'CAIATL': 'Caiatl',
    'ZAVALA': 'Zavala',
    'OSIRIS': 'Osiris',
    # 2026-11: D1 + D2 speaker normalization (v0.30.0/v0.31.0). The DB was
    # folded in place; these stay so a fresh rebuild keeps the same speakers.
    'HOLLIDAY': 'Amanda Holliday',
    'AMANDA': 'Amanda Holliday',
    'Amanda': 'Amanda Holliday',
    'Holliday': 'Amanda Holliday',
    'Anastasia': 'Anastasia Bray',
    'Asher': 'Asher Mir',
    'Ana': 'Ana Bray',
    'Devrim': 'Devrim Kay',
    'Sjur Eido': 'Eido',
    'Empress Caiatl': 'Caiatl',
    'Eva': 'Eva Levante',
    'The Exo Stranger': 'Exo Stranger',
    'Elisabeth Bray': 'Elsie Bray',
    'Fikrul': 'Fikrul, the Fanatic',
    'The Fanatic': 'Fikrul, the Fanatic',
    'Emissary (Orin)': 'Emissary',
    'Orin': 'Emissary',
    'The Emissary': 'Emissary',
    'GHOST': 'Ghost',
    'Ixix, Apothecary': 'Ixis, Apothecary',
    'Queen Mars Sov': 'Mara Sov',
    'Sathona': 'Savathûn',
    'Xi Ro': 'Xivu Arath',
    'Shiro': 'Shiro-4',
    'The Spider': 'Spider',
    'Nine': 'The Nine',
    'Tyra': 'Tyra Karn',
    "Tyra Karn's Voice": 'Tyra Karn',
    'Female voice': 'Unknown female voice',
    'Unidentified Female': 'Unknown female voice',
    'The Witness': 'Witness',
    'Zaval': 'Zavala',
    'Auryx': 'Oryx',
    'The Drifter': 'Drifter',
    'The Crow': 'Crow',
    # The Menagerie narrator is titled in-game; the corpus speaker is Calus.
    'Emperor Calus': 'Calus',
    # Caption prefixes use short forms; the corpus keeps full names. The bare
    # 'Petra' rows in the House of Wolves missions are Petra Venj.
    'Petra': 'Petra Venj',
    'Uldren': 'Uldren Sov',
    # Saint-14 is one character under many names; alias them so no source
    # variant fragments the corpus or trips the Roman-numeral speaker filter.
    'Saint-XIV': 'Saint-14',
    'Saint XIV': 'Saint-14',
    'Saint IV': 'Saint-14',
    'The Saint': 'Saint-14',
    'Saint': 'Saint-14',
    'Kellbreaker': 'Saint-14',
}

def canon_speaker(sp):
    return SPEAKER_ALIASES.get(sp, sp)

def deep_unescape(s):
    """Unescape repeatedly: some Ishtar pages are double-escaped (&amp;amp;)."""
    import html as _html
    if not s:
        return s
    for _ in range(4):
        u = _html.unescape(s)
        if u == s:
            break
        s = u
    return s

def parse_speaker_line(ln):
    m = re.match(r'^\*(?:The )?(.+?):\*\s*(.*)$', ln.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None

ROMAN_SUFFIX = re.compile(r'\b(?:I|II|III|IV|V|VI|VII|VIII|IX|X)$')
ACT_ONLY = re.compile(r'^Act (?:I|II|III)$')


def is_junk_speaker(sp):
    """Quest/step titles parsed as speakers by web scrapers, not characters.

    A speaker that resolves through SPEAKER_ALIASES is a mapped character and
    is never junk: 'Saint IV' must survive even though it ends in a Roman
    numeral, because it aliases to Saint-14."""
    sp = (sp or '').strip()
    if not sp:
        return False
    if sp in SPEAKER_ALIASES:
        return False
    # Never drop a Saint-* speaker: Destiny has exactly one Saint, and a dropped
    # row is unrecoverable while a kept row can always be aliased later.
    if re.match(r'^(?:the\s+)?saint\b', sp, re.I):
        return False
    if sp.upper() in ('NOTE', 'NOTES', 'AREA', 'REMEMBER', 'STATUS', 'WARNING',
                      'CAUTION', 'LOCATION', 'OBJECTIVE', 'REWARD', 'REWARDS'):
        return True
    return bool(ROMAN_SUFFIX.search(sp) or ACT_ONLY.match(sp))


def norm_text(s):
    """Normalize text for fast substring matching."""
    s = s.lower()
    s = s.replace('…','...').replace('’',"'").replace('—','-').replace('–','-')
    n = re.sub(r'[^a-z0-9 ]+',' ',s)
    n = re.sub(r'\s+',' ',n).strip()
    if n:
        return n
    # Punctuation-only canon lines (":)", "?", "...") must stay verifiable:
    # fall back to the lowered text with LIKE wildcards removed.
    return re.sub(r'\s+', ' ', s.replace('%', ' ').replace('_', ' ')).strip()

# In-universe Destiny timeline: story chapters in chronological order.
# Rows store the chapter slug in `timeline`; timeline_chapters carries rank+label.
TIMELINE_CHAPTERS = [
    (1, 'pre_history', 'Pre-History'),
    (2, 'ancient_past', 'Ancient Past'),
    (3, 'pre_golden_age', 'Pre-Golden Age'),
    (4, 'golden_age', 'Golden Age'),
    (5, 'the_collapse', 'The Collapse and the Exodus'),
    (6, 'the_dark_age', 'The Dark Age'),
    (7, 'the_city_age', 'The City Age (before the Guardian)'),
    (8, 'the_rise_of_the_guardian', 'The Rise of the Guardian (Destiny 1)'),
    (9, 'the_dark_below', "Crota's War on the Moon (The Dark Below)"),
    (10, 'house_of_wolves', 'The House of Wolves'),
    (11, 'the_taken_war', 'The Taken War (The Taken King)'),
    (12, 'the_siva_crisis', 'The Siva Crisis (Rise of Iron, Age of Triumph)'),
    (13, 'the_red_war', 'The Red War (Destiny 2)'),
    (14, 'the_curse_of_osiris', 'The Curse of Osiris'),
    (15, 'the_warmind_crisis', 'The Warmind Crisis'),
    (16, 'the_sack_of_the_dreaming_city', "Forsaken: Cayde's Murder and the Sack of the Dreaming City"),
    (17, 'the_nightmares_return', 'Shadowkeep: The Nightmares Return'),
    (18, 'the_rise_of_stasis', 'Beyond Light: The Rise of Stasis'),
    (19, 'the_witch_queen', 'The Witch Queen'),
    (20, 'the_lightfall', 'Lightfall'),
    (21, 'the_final_shape', 'The Final Shape'),
    (22, 'the_edge_of_fate', 'The Edge of Fate'),
    (23, 'renegades', 'Renegades'),
]

EXPANSION_CHAPTERS = {
    'destiny-1': 'the_rise_of_the_guardian',
    'the-dark-below': 'the_dark_below',
    'house-of-wolves': 'house_of_wolves',
    'the-taken-king': 'the_taken_war',
    'rise-of-iron': 'the_siva_crisis',
    'age-of-triumph': 'the_siva_crisis',
    'destiny-2': 'the_red_war',
    'curse-of-osiris': 'the_curse_of_osiris',
    'warmind': 'the_warmind_crisis',
    'forsaken': 'the_sack_of_the_dreaming_city',
    'shadowkeep': 'the_nightmares_return',
    'beyond-light': 'the_rise_of_stasis',
    '30th-anniversary': 'the_rise_of_stasis',
    'the-witch-queen': 'the_witch_queen',
    'lightfall': 'the_lightfall',
    'the-final-shape': 'the_final_shape',
    'the-edge-of-fate': 'the_edge_of_fate',
    'renegades': 'renegades',
}


def _tkey(value):
    return re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')


def _scene_flashback(*texts):
    """When-spooken rule: a scene explicitly set in the past wins over the
    content's release position. Strong markers only (arc/title), so modern
    dialogue merely *about* the Dark Age stays in its own chapter."""
    blob = ' '.join(t or '' for t in texts).lower()
    if 'golden age' in blob:
        return 'golden_age'
    if 'dark age' in blob:
        return 'the_dark_age'
    if 'distributary' in blob:
        return 'the_collapse'
    return None


ISHTAR_SNAPSHOT = os.path.join(ROOT, 'source', 'ishtar-timeline.json')


def load_ishtar():
    """Curated eras from the Ishtar timeline snapshot: source path -> chapter.
    Ishtar tags when a story event happens (about-time), which is the natural
    time for lore books, records and items; dialogue keeps the when-spoken
    derivation below. Missing snapshot or unmapped era -> None (fallback)."""
    if not os.path.exists(ISHTAR_SNAPSHOT):
        return {}
    out = {}
    for era in json.load(open(ISHTAR_SNAPSHOT, encoding='utf-8')).get('eras', []):
        if era.get('chapter'):
            for path in era.get('paths', []):
                out.setdefault(path, era['chapter'])
    return out


def _ishtar_path(url):
    if not url or 'ishtar-collective.net' not in url:
        return None
    return '/' + '/'.join(url.split('/')[3:])


def derive_timeline(conn):
    """Tag rows with their in-universe story chapter (the Destiny timeline).

    transcripts: scene flashback > classification > release-name, then the
    release-driven tables, books/records via document_classification, and
    character_lines inherit their source transcript. NULL means unknown.
    """
    for rank, slug, label in TIMELINE_CHAPTERS:
        conn.execute('INSERT OR REPLACE INTO timeline_chapters (rank,slug,label) VALUES (?,?,?)',
                     (rank, slug, label))

    exp_keys = {}
    for slug, name in conn.execute('SELECT slug, name FROM expansions').fetchall():
        exp_keys.setdefault(_tkey(name), slug)
        exp_keys.setdefault(_tkey(slug), slug)
    season_to_exp = {}
    for slug, name, exp in conn.execute(
            'SELECT slug, name, expansion_slug FROM seasons').fetchall():
        for key in (_tkey(slug), _tkey(name)):
            if key:
                season_to_exp.setdefault(key, exp)
        tail = re.sub(r'^(season-of-the-|season-of-|season-|episode-)', '', slug)
        if tail and len(tail) >= 4:
            season_to_exp.setdefault(tail, exp)
    aliases = {'ttk': 'the-taken-king'}

    def resolve_release(release):
        """release text -> expansion slug, so one chapter map covers it all."""
        if not release:
            return None, None
        text = re.sub(r'\([^)]*\)', ' ', release)  # drop (Beta), (2015.05.09), (April Update)
        parts = [p for p in re.split(r'[/]', text) if p.strip()] or [text]
        for part in parts:
            key = _tkey(part)
            if not key:
                continue
            if key in aliases:
                return aliases[key], 'release_name'
            if key in season_to_exp and season_to_exp[key]:
                return season_to_exp[key], 'release_name'
            if key in exp_keys:
                return exp_keys[key], 'release_name'
            for skey, exp in season_to_exp.items():
                if exp and len(key) >= 6 and (skey.endswith('-' + key) or key.endswith('-' + skey)):
                    return exp, 'release_name'
            for ekey, exp in exp_keys.items():
                if len(key) >= 8 and ekey.endswith('-' + key):
                    return exp, 'release_name'
        return None, None

    def chapter_for(exp_slug):
        return EXPANSION_CHAPTERS.get(exp_slug) if exp_slug else None

    stats = {}
    ishtar = load_ishtar()
    ishtar_hits = 0

    def ishtar_chapter(url):
        path = _ishtar_path(url)
        return ishtar.get(path) if path else None

    class_by_tid = {tid: (season, exp) for tid, season, exp in conn.execute(
        'SELECT transcript_id, season_slug, expansion_slug FROM transcript_classification')}
    season_exp = {slug: exp for slug, exp in conn.execute(
        'SELECT slug, expansion_slug FROM seasons')}

    n = 0
    for tid, title, release, arc in conn.execute(
            'SELECT id, title, release, arc FROM transcripts'):
        chapter = basis = None
        flash = _scene_flashback(arc, title)
        if flash:
            chapter, basis = flash, 'scene_flashback'
        else:
            season, exp = class_by_tid.get(tid, (None, None))
            chapter = chapter_for(exp or season_exp.get(season))
            if chapter:
                basis = 'classification'
            else:
                exp_slug, basis = resolve_release(release)
                chapter = chapter_for(exp_slug)
                if not chapter:
                    basis = None
        conn.execute('UPDATE transcripts SET timeline=?, timeline_basis=? WHERE id=?',
                     (chapter, basis, tid))
        n += bool(chapter)
    stats['transcripts'] = n

    n = 0
    for rid, release, url in conn.execute(
            'SELECT id, release, source_url FROM interactions'):
        exp_slug, basis = resolve_release(release)
        chapter = chapter_for(exp_slug)
        conn.execute('UPDATE interactions SET timeline=?, timeline_basis=? WHERE id=?',
                     (chapter, basis if chapter else None, rid))
        n += bool(chapter)
    stats['interactions'] = n

    n = 0
    for rid, release in conn.execute('SELECT id, release FROM items'):
        exp_slug, basis = resolve_release(release)
        chapter = chapter_for(exp_slug)
        conn.execute('UPDATE items SET timeline=?, timeline_basis=? WHERE id=?',
                     (chapter, basis if chapter else None, rid))
        n += bool(chapter)
    # Ishtar's curated era wins where the item appears on the timeline: it
    # records when the item's story happens, not when it shipped.
    for rid, url in conn.execute(
            "SELECT id, source_url FROM items WHERE source_url LIKE '%ishtar-collective.net%'"):
        chapter = ishtar_chapter(url)
        if chapter:
            conn.execute('UPDATE items SET timeline=?, timeline_basis=? WHERE id=?',
                         (chapter, 'ishtar_timeline', rid))
            ishtar_hits += 1
            n += 1
    stats['items'] = n

    # books and records: story position from document_classification; records
    # fall back to their release text when unclassified.
    n_rec = n_book = 0
    for source, sid, season, exp in conn.execute(
            'SELECT source, source_id, season_slug, expansion_slug FROM document_classification'):
        exp = exp or season_exp.get(season)
        chapter = chapter_for(exp)
        if source == 'book':
            conn.execute('UPDATE books SET timeline=?, timeline_basis=? WHERE id=?',
                         (chapter, 'classification' if chapter else None, sid))
            n_book += bool(chapter)
        elif source == 'record':
            conn.execute('UPDATE records SET timeline=?, timeline_basis=? WHERE id=?',
                         (chapter, 'classification' if chapter else None, sid))
            n_rec += bool(chapter)
    for rid, release in conn.execute(
            'SELECT id, release FROM records WHERE timeline IS NULL'):
        exp_slug, basis = resolve_release(release)
        chapter = chapter_for(exp_slug)
        if chapter:
            conn.execute('UPDATE records SET timeline=?, timeline_basis=? WHERE id=?',
                         (chapter, basis, rid))
            n_rec += 1
    # Ishtar wins for records and books it carries: curated event time.
    stats['books'] = n_book
    stats['records'] = n_rec
    for table, key in (('records', 'records'), ('books', 'books')):
        n_extra = 0
        for rid, url in conn.execute(
                f"SELECT id, source_url FROM {table} "
                "WHERE source_url LIKE '%ishtar-collective.net%'"):
            chapter = ishtar_chapter(url)
            if chapter:
                conn.execute(f'UPDATE {table} SET timeline=?, timeline_basis=? WHERE id=?',
                             (chapter, 'ishtar_timeline', rid))
                ishtar_hits += 1
                n_extra += 1
        stats[key] = stats.get(key, 0) + n_extra
    # grimoire cards: Ishtar is their only timeline (content time of the tale)
    n_cards = 0
    for rid, url in conn.execute(
            "SELECT id, source_url FROM grimoire_cards "
            "WHERE source_url LIKE '%ishtar-collective.net%'"):
        chapter = ishtar_chapter(url)
        if chapter:
            conn.execute('UPDATE grimoire_cards SET timeline=?, timeline_basis=? WHERE id=?',
                         (chapter, 'ishtar_timeline', rid))
            ishtar_hits += 1
            n_cards += 1
    stats['grimoire_cards'] = n_cards
    stats['ishtar_applied'] = ishtar_hits

    conn.execute(
        "UPDATE character_lines SET timeline = "
        "(SELECT t.timeline FROM transcripts t WHERE t.slug = character_lines.source_slug) "
        "WHERE source_type = 'transcript'")
    stats['character_lines'] = conn.execute(
        'SELECT COUNT(*) FROM character_lines WHERE timeline IS NOT NULL').fetchone()[0]
    return stats


def _caption_pkg(url):
    """Split a caption provenance URL 'pkg:<package_base>#<entry>'.

    Unlinked banks carry no StringReference entry ('pkg:<base>#None'), which
    is provenance worth keeping (source_entry stays NULL) rather than dropping.
    """
    m = re.match(r'^pkg:([^#]+)#(\d+)$', url or '')
    if m:
        return m.group(1), int(m.group(2))
    if url and url.startswith('pkg:'):
        return url[4:].split('#')[0] or None, None
    return None, None


def _caption_prov(conn, line_id, line, rec, src_pkg, src_entry):
    """Attach one caption line's StringReference provenance.

    INSERT OR IGNORE: several caption tables can carry the same canon line, and
    caption_provenance has one row per line. Returns 1 when a row was written.
    """
    cur = conn.execute(
        'INSERT OR IGNORE INTO caption_provenance '
        '(line_id,hash,kind,source_pkg,source_entry,bank_entry) VALUES (?,?,?,?,?,?)',
        (line_id, line.get('hash'), rec.get('kind_class'), src_pkg, src_entry,
         rec.get('bank_entry')))
    return cur.rowcount


def _caption_header(conn, rec, acts, stats):
    """Insert a caption transcript header and its taxonomy row.

    The activity facet comes from the curated extraction pass and is stored
    with confidence='derived' (season/expansion filled from the activity
    catalogue, exactly as classify() would). Everything else is 'unknown':
    caption text spans every era, so no season is ever inferred from it.
    """
    speaker = canon_speaker(rec.get('speaker') or 'Cutscene')
    attributed = speaker not in ('Cutscene', 'Narration')
    title = speaker if attributed else 'Game caption (%s)' % (
        rec.get('kind_class') or 'caption')
    cur = conn.execute(
        'INSERT INTO transcripts (slug,title,release,characters,arc,source_url,'
        'source_tier,lang) VALUES (?,?,?,?,?,?,?,?)',
        (rec['slug'], title, '', speaker if attributed else '', '', '',
         'game_caption', rec.get('lang') or 'en'))
    tid = cur.lastrowid
    stats['transcripts'] += 1
    row = acts.get(taxonomy.CAPTION_ACTIVITY_SLUGS.get(rec.get('activity'), ''))
    if rec.get('activity') and not row:
        # A facet key with no taxonomy slug must be visible in the build log:
        # silently dropping it hides an extraction/taxonomy vocabulary drift.
        stats['unresolved_facets'] += 1
    if row and rec.get('confidence') == 'derived':
        conn.execute(
            'INSERT OR REPLACE INTO transcript_classification '
            '(transcript_id,activity_slug,activity_type,season_slug,act,event_slug,'
            'expansion_slug,confidence,evidence) VALUES (?,?,?,?,?,?,?,?,?)',
            (tid, row[0], row[1], row[2], None, None, row[3], 'derived',
             'caption_narration_curation'))
        stats['facets'] += 1
    else:
        conn.execute(
            'INSERT OR REPLACE INTO transcript_classification '
            '(transcript_id,confidence,evidence) VALUES (?,?,?)',
            (tid, 'unknown', ''))
    return tid


def load_captions(conn):
    """Load English game captions from archive/data/captions.jsonl.

    One record is one caption table extracted from the local build: a
    transcript header (source_tier='game_caption', lang='en'), its lines, a
    taxonomy row, and per-line StringReference provenance in caption_provenance.

    Rules:
      * speakers canonicalise through SPEAKER_ALIASES like every other loader;
      * a line whose normalized text already exists anywhere in canon is not
        inserted a second time -- its provenance attaches to the existing line,
        so search never returns the same text twice and no attribution
        conflict is introduced;
      * the activity facet is the curated extraction verdict; every other
        transcript stays 'unknown'. Never guess a season from caption text.

    Runs after taxonomy.populate() so keyword classification cannot overwrite
    the curated facets, and before the FTS build so caption rows are indexed
    with source='caption'.
    """
    path = os.path.join(ROOT, 'archive', 'data', 'captions.jsonl')
    stats = {'transcripts': 0, 'lines': 0, 'already_in_canon': 0,
             'provenance': 0, 'facets': 0, 'unresolved_facets': 0}
    if not os.path.exists(path):
        return stats

    # norm_line -> canon line id (lowest id first: deterministic, and a caption
    # line that already exists attaches its provenance to that row).
    canon = {}
    for lid, nl in conn.execute(
            "SELECT id, norm_line FROM transcript_lines WHERE norm_line != '' ORDER BY id"):
        canon.setdefault(nl, lid)

    # Activity catalogue fill for the curated facets (type/season/expansion).
    acts = {r[0]: r for r in conn.execute(
        'SELECT slug, activity_type, season_slug, expansion_slug FROM activities')}

    for raw in open(path, encoding='utf-8'):
        rec = json.loads(raw)
        src_pkg, src_entry = _caption_pkg(rec.get('source_url', ''))
        tid, seq = None, 0
        for line in rec.get('lines', []):
            text = (line.get('text') or '').strip()
            if not text:
                continue
            nl = norm_text(text)
            hit = canon.get(nl)
            if hit is not None:
                # caption sees a newer attribution for a canon line: adopt it
                # only when the canon row has no source yet, and never
                # rewrite anyone's attribution.
                line_ss = (line.get('speaker_source') or '').strip() or None
                if line_ss:
                    conn.execute(
                        'UPDATE transcript_lines SET speaker_source=? '
                        'WHERE id=? AND speaker_source IS NULL',
                        (line_ss, hit))
                stats['provenance'] += _caption_prov(
                    conn, hit, line, rec, src_pkg, src_entry)
                stats['already_in_canon'] += 1
                continue
            if tid is None:      # header appears only when a line is new
                tid = _caption_header(conn, rec, acts, stats)
            speaker = canon_speaker(
                line.get('speaker') or rec.get('speaker') or 'Cutscene')
            line_ss = (line.get('speaker_source') or '').strip() or None
            lid = conn.execute(
                'INSERT INTO transcript_lines (transcript_id,seq,speaker,line,'
                'norm_line,is_stage_dir,speaker_source) VALUES (?,?,?,?,?,?,?)',
                (tid, seq, speaker, text, nl,
                 1 if line.get('is_stage_dir') else 0, line_ss)).lastrowid
            canon.setdefault(nl, lid)
            seq += 1
            stats['lines'] += 1
            stats['provenance'] += _caption_prov(
                conn, lid, line, rec, src_pkg, src_entry)
    return stats


def migrate():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    # A crashed build can leave WAL sidecars behind; stale ones applied to a
    # fresh file surface as "database disk image is malformed" mid-build.
    for suffix in ('-wal', '-shm'):
        stale = DB_PATH + suffix
        if os.path.exists(stale):
            os.remove(stale)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(open(SCHEMA).read())
    taxonomy.ensure_schema(conn)

    # Books
    books = glob.glob(os.path.join(ROOT, 'source', 'books', '*.md'))
    book_count = 0
    entry_count = 0
    # Live Ishtar book URLs use categories/book-<slug>, except two books that
    # live at their plain slug (verified against the live /books listing).
    BOOK_PREFIX_EXEMPT = {'books-of-sorrow', 'the-maraid'}
    for path in books:
        slug = os.path.basename(path)[:-3]
        live_slug = slug if slug in BOOK_PREFIX_EXEMPT else f'book-{slug}'
        title, sections, _ = parse_md_sections(path)
        cur = conn.execute('INSERT INTO books (slug,title,source_url,entry_count) VALUES (?,?,?,?)',
            (live_slug, title, f'https://www.ishtar-collective.net/categories/{live_slug}', len(sections)))
        bid = cur.lastrowid
        book_count += 1
        for i, (st, sb) in enumerate(sections):
            conn.execute('INSERT INTO book_entries (book_id,title,body,norm_text,seq) VALUES (?,?,?,?,?)',
                (bid, st, sb, norm_text(sb), i))
            entry_count += 1
    print(f'books: {book_count}, entries: {entry_count}')

    # Transcripts
    transcripts = glob.glob(os.path.join(ROOT, 'source', 'transcripts', '*.md'))
    t_count = 0
    tl_count = 0
    for path in transcripts:
        slug = os.path.basename(path)[:-3]
        if slug == 'index':
            continue
        text = open(path, encoding='utf-8', errors='ignore').read()
        lines = text.split('\n')
        title = lines[0].lstrip('# ').strip() if lines else ''
        release = ''
        characters = ''
        arc = ''
        tier = 'ishtar_main'
        source_url = f'https://www.ishtar-collective.net/transcripts/{slug}'
        for ln in lines[:20]:
            if ln.startswith('- Release:'):
                release = ln.replace('- Release:','').strip()
            elif ln.startswith('- Characters:'):
                characters = ln.replace('- Characters:','').strip()
            elif ln.startswith('- Arc:'):
                arc = ln.replace('- Arc:','').strip()
            elif ln.startswith('- Tier:'):
                tier = ln.replace('- Tier:','').strip()
            elif ln.startswith('- Source:'):
                raw_source = ln.replace('- Source:','').strip()
                # Older hand-written files describe the source in prose
                # ("Destinypedia — https://..."). Keep the URL when present.
                m = re.search(r'https?://\S+', raw_source)
                source_url = m.group(0) if m else ''
        cur = conn.execute(
            'INSERT INTO transcripts (slug,title,release,characters,arc,source_url,source_tier) VALUES (?,?,?,?,?,?,?)',
            (slug, title, release, characters, arc, source_url, tier))
        tid = cur.lastrowid
        t_count += 1
        seq = 0
        section = ''
        optional = 0
        class_tag = ''
        # Audio-quoted line format: '- "quote text"' (no *Speaker:* wrapper)
        is_quoted_file = slug.startswith(('ingame-quotes-', 'youtube-', 'weblore-'))
        for ln in lines:
            st = ln.strip()
            if st.startswith('## '):
                section = st[3:].strip()
                continue
            if st == '<!-- optional -->':
                optional = 1
                continue
            if st == '<!-- /optional -->':
                optional = 0
                continue
            if st.startswith('<!-- class:'):
                class_tag = st.split(':', 1)[1].replace('-->', '').strip().lower()
                continue
            if st == '<!-- /class -->':
                class_tag = ''
                continue
            if is_quoted_file:
                m = re.match(r'^-?\s*"(.+?)"\s*(?:(?:-|\u2014)\s*\w.*\s*)?$', ln.strip())
                if m:
                    line = m.group(1).strip()
                    conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir,section,is_optional,class_tag) VALUES (?,?,?,?,?,0,?,?,?)',
                        (tid, seq, 'Drifter', line, norm_text(line), section, optional, class_tag or None))
                    seq += 1
                    tl_count += 1
                continue
            sp, line = parse_speaker_line(ln)
            if sp and line and not is_junk_speaker(sp):
                conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir,section,is_optional,class_tag) VALUES (?,?,?,?,?,0,?,?,?)',
                    (tid, seq, sp, line, norm_text(line), section, optional, class_tag or None))
                seq += 1
                tl_count += 1
            elif not is_quoted_file and len(ln.strip()) > 20 and not ln.startswith('#') and not ln.startswith('-'):
                # Stage direction / narration line
                conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir,section,is_optional,class_tag) VALUES (?,?,?,?,?,1,?,?,?)',
                    (tid, seq, 'Narration', ln.strip(), norm_text(ln.strip()), section, optional, class_tag or None))
                seq += 1
                tl_count += 1
    print(f'transcripts: {t_count}, lines: {tl_count}')

    # Web transcript pages (archive/data/transcripts_web.jsonl, scraped from Ishtar)
    # Junk speakers are footer "related content" blocks, not dialogue.
    web_jsonl = os.path.join(ROOT, 'archive', 'data', 'transcripts_web.jsonl')
    if os.path.exists(web_jsonl):
        import html as html_mod
        JUNK_SPEAKERS = {'Category', 'Quest', 'Ghost Scan', 'Sources', 'Note', 'Dialogue Option for the Field Assignment'}
        releases_path = os.path.join(ROOT, 'archive', 'data', 'transcript-releases.json')
        releases = {}
        if os.path.exists(releases_path):
            releases = json.load(open(releases_path, encoding='utf-8'))
        covered = set()
        for r in conn.execute('SELECT slug FROM transcripts').fetchall():
            covered.add(r[0])
        w_count = 0
        wl_count = 0
        for ln in open(web_jsonl, encoding='utf-8'):
            try:
                d = json.loads(ln)
            except Exception:
                continue
            slug = d.get('slug', '')
            if not slug or slug in covered:
                continue
            covered.add(slug)
            release = (releases.get(slug) or {}).get('release', '')
            cur = conn.execute('INSERT INTO transcripts (slug,title,release,characters,arc,source_url,source_tier) VALUES (?,?,?,?,?,?,?)',
                (slug, d.get('title', ''), release, '', '', d.get('source_url', ''), 'ishtar_web'))
            tid = cur.lastrowid
            w_count += 1
            seen_page = set()
            seq = 0
            page_lines = list(d.get('lines', []))
            # Ishtar pages open with a "by <contributor>" credit and close with
            # a related-content browser. Neither is transcript text.
            while page_lines:
                head = deep_unescape(page_lines[0].get('text', '')).strip()
                if re.fullmatch(r'by [A-Za-z0-9 ._&\'-]{1,40}', head):
                    page_lines.pop(0)
                    continue
                break
            for line in page_lines:
                sp = line.get('speaker', '')
                txt = deep_unescape(line.get('text', '')).strip()
                if txt.startswith('Discuss this Transcript') or txt == 'TheIshtarCollective':
                    break
                if re.fullmatch(r'\[\s*(Music|Applause|Laughter|Cheering)\s*\]', txt, re.I):
                    continue
                # YouTube chapter markers parse as speaker lines:
                # "Cutscene begins at 01:49 and ends at 4:59"
                if re.match(r'^Cutscene (begins|starts) at', sp):
                    continue
                if sp in JUNK_SPEAKERS or not txt or is_junk_speaker(sp):
                    continue
                key = (sp, txt)
                if key in seen_page:
                    continue
                seen_page.add(key)
                stage = 0 if sp else 1
                if not sp:
                    sp = 'Narration'
                conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir) VALUES (?,?,?,?,?,?)',
                    (tid, seq, sp, txt, norm_text(txt), stage))
                seq += 1
                wl_count += 1
        print(f'web transcripts: {w_count}, web lines: {wl_count}')
        t_count += w_count
        tl_count += wl_count

    # Cutscene transcripts (archive/data/cutscenes.jsonl, YouTube captions)
    # Lines start as speaker 'Cutscene'; unique-match attribution runs after.
    cut_jsonl = os.path.join(ROOT, 'archive', 'data', 'cutscenes.jsonl')
    if os.path.exists(cut_jsonl):
        STAGE_DIR = re.compile(r'^\[[^\]]+\]$')
        covered = set(r[0] for r in conn.execute('SELECT slug FROM transcripts').fetchall())
        c_count = 0
        cl_count = 0
        for ln in open(cut_jsonl, encoding='utf-8'):
            try:
                d = json.loads(ln)
            except Exception:
                continue
            slug = d.get('slug', '')
            if not slug or slug in covered:
                continue
            covered.add(slug)
            cur = conn.execute('INSERT INTO transcripts (slug,title,release,characters,arc,source_url,source_tier) VALUES (?,?,?,?,?,?,?)',
                (slug, d.get('title', ''), 'Cutscene', '', '', d.get('source_url', ''), 'cutscene'))
            tid = cur.lastrowid
            c_count += 1
            seq = 0
            seen = set()
            for line in d.get('lines', []):
                txt = line.get('text', '').strip()
                if not txt or txt in seen:
                    continue
                seen.add(txt)
                if STAGE_DIR.match(txt):
                    sp, stage = 'Narration', 1
                else:
                    sp, stage = 'Cutscene', 0
                conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir) VALUES (?,?,?,?,?,?)',
                    (tid, seq, sp, txt, norm_text(txt), stage))
                seq += 1
                cl_count += 1
        # Attribute cutscene lines whose normalized text uniquely matches a known speaker
        attributed = conn.execute("""
            UPDATE transcript_lines SET speaker = (
                SELECT t2.speaker FROM transcript_lines t2
                WHERE t2.norm_line = transcript_lines.norm_line
                  AND t2.speaker NOT IN ('Cutscene','Narration')
                GROUP BY t2.speaker LIMIT 1
            )
            WHERE speaker = 'Cutscene'
              AND (SELECT COUNT(DISTINCT t3.speaker) FROM transcript_lines t3
                   WHERE t3.norm_line = transcript_lines.norm_line
                     AND t3.speaker NOT IN ('Cutscene','Narration')) = 1
        """).rowcount
        print(f'cutscene transcripts: {c_count}, lines: {cl_count}, attributed: {attributed}')
        t_count += c_count
        tl_count += cl_count

    # Canonicalize speaker aliases across every loader (transcripts + interactions)
    for alias, canon in SPEAKER_ALIASES.items():
        conn.execute('UPDATE transcript_lines SET speaker=? WHERE speaker=?', (canon, alias))
        conn.execute('UPDATE interactions SET speaker=? WHERE speaker=?', (canon, alias))
        conn.execute('INSERT OR REPLACE INTO speaker_aliases (alias, canonical) VALUES (?,?)', (alias, canon))

    # Grimoire cards
    cards = glob.glob(os.path.join(ROOT, 'source', 'cards', '*.md'))
    g_count = 0
    for path in cards:
        slug = os.path.basename(path)[:-3]
        text = open(path, encoding='utf-8', errors='ignore').read()
        lines = text.split('\n')
        title = lines[0].lstrip('# ').strip() if lines else ''
        body = '\n'.join(lines[2:]).strip()
        src_url = ''
        for ln in lines[:6]:
            if ln.strip().startswith('- Source:'):
                src_url = ln.split('Source:', 1)[1].strip()
                break
        if not src_url:
            src_url = f'https://www.ishtar-collective.net/entries/{slug}'
        conn.execute('INSERT OR IGNORE INTO grimoire_cards (slug,title,body,norm_body,game,source_url) VALUES (?,?,?,?,?,?)',
            (slug, title, body, norm_text(body), 'Destiny 1', src_url))
        g_count += 1
    print(f'grimoire cards: {g_count}')

    # Interactions (from JSONL if exists, else from markdown)
    int_jsonl = os.path.join(ROOT, 'archive', 'data', 'interactions.jsonl')
    i_count = 0
    if os.path.exists(int_jsonl):
        seen = set()
        for ln in open(int_jsonl, encoding='utf-8'):
            try:
                d = json.loads(ln)
                slug = d.get('slug','')
                if slug in seen: continue
                seen.add(slug)
                conn.execute('INSERT OR IGNORE INTO interactions (slug,title,speaker,text,norm_text,release,source_url) VALUES (?,?,?,?,?,?,?)',
                    (slug, d.get('title',''), d.get('speaker',''), d.get('text',''), norm_text(d.get('text','')), d.get('release',''), d.get('url','')))
                i_count += 1
            except: pass
    print(f'interactions: {i_count}')

    # Items (from JSONL)
    items_jsonl = os.path.join(ROOT, 'archive', 'data', 'items.jsonl')
    it_count = 0
    if os.path.exists(items_jsonl):
        seen = set()
        for ln in open(items_jsonl, encoding='utf-8'):
            try:
                d = json.loads(ln)
                slug = d.get('slug','')
                if slug in seen: continue
                seen.add(slug)
                itext = deep_unescape(d.get('text',''))
                conn.execute('INSERT OR IGNORE INTO items (slug,title,text,norm_text,release,item_type,source_url) VALUES (?,?,?,?,?,?,?)',
                    (slug, deep_unescape(d.get('title','')), itext, norm_text(itext), deep_unescape(d.get('release','')), deep_unescape(d.get('type','')), d.get('url','')))
                it_count += 1
            except: pass
    print(f'items: {it_count}')

    # Records (from index.json + entries)
    rec_jsonl = os.path.join(ROOT, 'archive', 'data', 'records.jsonl')
    r_count = 0
    if os.path.exists(rec_jsonl):
        for ln in open(rec_jsonl, encoding='utf-8'):
            try:
                d = json.loads(ln)
                conn.execute('INSERT OR IGNORE INTO records (slug,title,body,norm_body,release,source_url) VALUES (?,?,?,?,?,?)',
                    (d.get('slug',''), d.get('title',''), d.get('body',''), d.get('release',''), d.get('url','')))
                r_count += 1
            except: pass
    else:
        # Read from source markdown
        base = os.path.join(ROOT, 'source', 'records')
        for path in sorted(glob.glob(os.path.join(base, '*.md'))):
            slug = os.path.basename(path)[:-3]
            text = open(path, encoding='utf-8', errors='ignore').read()
            lines = text.split('\n')
            title = lines[0].lstrip('# ').strip() if lines else ''
            # Extract body: skip title line, meta lines, spacer
            body_lines = []
            started = False
            for ln in lines[1:]:
                if ln.startswith(('- Source:','- Release:','- Key Lore:')):
                    started = True
                    continue
                if started:
                    body_lines.append(ln)
            body = '\n'.join(body_lines).strip()
            # parse release from meta
            rel = ''
            for ln in lines[:5]:
                if ln.startswith('- Release:'):
                    rel = ln.replace('- Release:','').strip()
            conn.execute('INSERT OR IGNORE INTO records (slug,title,body,norm_body,release,source_url) VALUES (?,?,?,?,?,?)',
                (slug, title, body, norm_text(body), rel, f'https://www.ishtar-collective.net/records/{slug}'))
            r_count += 1
    print(f'records: {r_count}')

    # Characters + character_lines (from compendium)
    comp_dir = os.path.join(ROOT, 'compendium', 'characters')
    c_count = 0
    cl_count = 0
    if os.path.isdir(comp_dir):
        for path in sorted(glob.glob(os.path.join(comp_dir, '*.md'))):
            fn = os.path.basename(path)[:-3]
            if fn == 'minor':
                continue
            # slugify character name from filename
            name = fn.replace('-', ' ').title()
            # better: get name from first line
            text = open(path, encoding='utf-8', errors='ignore').read()
            first = text.split('\n')[0].lstrip('# ').strip()
            if first:
                name = first
            cur = conn.execute('INSERT OR IGNORE INTO characters (name,slug) VALUES (?,?)', (name, fn))
            cid = cur.lastrowid
            if cid:
                c_count += 1
            # Compendium lines are "- \"quote\" - source_slug". Some older entries
            # pack several quotes into one bullet (""A" - "B" ...") - split them.
            for line in text.split('\n'):
                m = re.match(r'^-\s+(.+?)\s+-\s+(\S+)\s*$', line)
                if not m:
                    continue
                body, src = m.group(1), m.group(2)
                for q in re.findall(r'"([^"]+)"', body):
                    q = q.strip()
                    if not q:
                        continue
                    conn.execute('INSERT INTO character_lines (character_id,text,norm_text,source_type,source_slug) VALUES (?,?,?,?,?)',
                        (cid, q, norm_text(q), 'transcript', src))
                    cl_count += 1
    print(f'characters: {c_count}, lines: {cl_count}')

    # Fill missing item types from duplicate titles, when the source has one
    conn.execute(
        "UPDATE items SET item_type=(SELECT b.item_type FROM items b "
        "WHERE b.title=items.title AND b.item_type != '' LIMIT 1) "
        "WHERE item_type='' AND EXISTS (SELECT 1 FROM items b "
        "WHERE b.title=items.title AND b.item_type != '')")

    # Activity / season / event taxonomy (additive; canon tables untouched)
    tax_stats = taxonomy.populate(conn)
    print(f'taxonomy: {tax_stats}')

    # In-universe Destiny timeline (story chapters) - after classification,
    # before the FTS build so every fts row carries its chapter.
    tl_stats = derive_timeline(conn)
    print(f'timeline: {tl_stats}')

    # Game captions (archive/data/captions.jsonl): English subtitle and callout
    # text from the local build. Loaded after taxonomy so the curated activity
    # facets survive, and before the FTS build so caption rows index as
    # source='caption'.
    cap_stats = load_captions(conn)
    print('captions: %(transcripts)d transcripts, %(lines)d lines, '
          '%(already_in_canon)d already in canon, %(provenance)d provenance rows, '
          '%(facets)d activity facets, %(unresolved_facets)d unresolved' % cap_stats)
    t_count += cap_stats['transcripts']
    tl_count += cap_stats['lines']

    # Build FTS index (global rowid sequence)
    print('building FTS index...')
    fts_id = 0
    tl_by_tid = dict(conn.execute('SELECT id, COALESCE(timeline, "") FROM transcripts'))
    tl_by_slug = dict(conn.execute('SELECT slug, COALESCE(timeline, "") FROM transcripts'))
    tl_interactions = dict(conn.execute('SELECT slug, COALESCE(timeline, "") FROM interactions'))
    tl_items = dict(conn.execute('SELECT slug, COALESCE(timeline, "") FROM items'))
    tl_records = dict(conn.execute('SELECT slug, COALESCE(timeline, "") FROM records'))
    tl_cards = dict(conn.execute('SELECT slug, COALESCE(timeline, "") FROM grimoire_cards'))
    tl_books = dict(conn.execute('SELECT slug, COALESCE(timeline, "") FROM books'))
    def add_fts(title, text, speaker='', body='', source='', source_slug='',
                class_tag='', timeline='', lang='en'):
        # lang is the document language: every row in this build is English,
        # later caption languages arrive as data rows (see capabilities.json).
        nonlocal fts_id
        fts_id += 1
        conn.execute('INSERT INTO fts (rowid,title,text,speaker,body,source,source_slug,class_tag,timeline,lang) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (fts_id, title, text or '', speaker, body or '', source, source_slug,
             class_tag, timeline or '', lang))
    for bid, slug, title in conn.execute('SELECT id,slug,title FROM books').fetchall():
        for eid, etitle, ebody in conn.execute('SELECT id,title,body FROM book_entries WHERE book_id=?', (bid,)).fetchall():
            add_fts(f'{title}: {etitle}', ebody, source='book_entry', source_slug=slug,
                    timeline=tl_books.get(slug, ''))
    for tid, slug, title, tier in conn.execute(
            'SELECT id, slug, title, source_tier FROM transcripts').fetchall():
        for tlid, sp, line, ctag in conn.execute(
                'SELECT id,speaker,line,class_tag FROM transcript_lines WHERE transcript_id=?', (tid,)).fetchall():
            # Game captions are their own source so search can rank and filter
            # them (`--type captions`); every other line stays transcript_line.
            add_fts(title, line, sp,
                    source='caption' if tier == 'game_caption' else 'transcript_line',
                    source_slug=slug, class_tag=ctag or '',
                    timeline=tl_by_tid.get(tid, ''))
    for gid, slug, title, body in conn.execute('SELECT id,slug,title,body FROM grimoire_cards').fetchall():
        add_fts(title, body, source='grimoire_card', source_slug=slug,
                timeline=tl_cards.get(slug, ''))
    for iid, slug, title, speaker, text in conn.execute('SELECT id,slug,title,speaker,text FROM interactions').fetchall():
        add_fts(title, text, speaker, source='interaction', source_slug=slug,
                timeline=tl_interactions.get(slug, ''))
    for iid, slug, title, text in conn.execute('SELECT id,slug,title,text FROM items').fetchall():
        if text:  # stat-only items have no searchable text
            add_fts(title, text, source='item', source_slug=slug,
                    timeline=tl_items.get(slug, ''))
    for rid, slug, title, body in conn.execute('SELECT id,slug,title,body FROM records').fetchall():
        add_fts(title, body, source='record', source_slug=slug,
                timeline=tl_records.get(slug, ''))
    print(f'fts entries: {fts_id}')

    # Verification index: normalized text with provenance (documents only)
    print('building verification index...')
    for sql in (
        "INSERT INTO verify_fts(norm, source, slug, speaker) "
        "SELECT tl.norm_line, "
        "CASE WHEN t.source_tier='game_caption' THEN 'caption' ELSE 'transcript' END, "
        "t.slug, tl.speaker "
        "FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id",
        "INSERT INTO verify_fts(norm, source, slug, speaker) "
        "SELECT e.norm_text, 'book', b.slug, '' "
        "FROM book_entries e JOIN books b ON b.id=e.book_id",
        "INSERT INTO verify_fts(norm, source, slug, speaker) "
        "SELECT norm_body, 'grimoire_card', slug, '' FROM grimoire_cards",
        "INSERT INTO verify_fts(norm, source, slug, speaker) "
        "SELECT norm_text, 'interaction', slug, speaker FROM interactions",
        "INSERT INTO verify_fts(norm, source, slug, speaker) "
        "SELECT norm_text, 'item', slug, '' FROM items WHERE text != ''",
        "INSERT INTO verify_fts(norm, source, slug, speaker) "
        "SELECT norm_body, 'record', slug, '' FROM records",
    ):
        conn.execute(sql)
    v_count = conn.execute('SELECT COUNT(*) FROM verify_fts').fetchone()[0]
    print(f'verification entries: {v_count}')

    conn.execute(
        "INSERT INTO item_title_fts(title, slug, item_type, release) "
        "SELECT title, slug, item_type, release FROM items WHERE title != ''")
    itf_count = conn.execute('SELECT COUNT(*) FROM item_title_fts').fetchone()[0]
    print(f'item title entries: {itf_count}')

    # Meta: a self-describing stamp for the shipped artifact. Every count key
    # must equal a live COUNT(*) (tests/test-db.sh enforces it).
    for k, v in [
        ('version',SCHEMA_VERSION),
        ('last_updated', time.strftime('%Y-%m-%d')),
        ('books', str(book_count)),
        ('book_entries', str(entry_count)),
        ('transcripts', str(t_count)),
        ('transcript_lines', str(tl_count)),
        ('grimoire_cards', str(g_count)),
        ('interactions', str(i_count)),
        ('items', str(it_count)),
        ('records', str(r_count)),
        ('characters', str(c_count)),
        ('character_lines', str(cl_count)),
        ('expansions', str(conn.execute('SELECT COUNT(*) FROM expansions').fetchone()[0])),
        ('seasons', str(conn.execute('SELECT COUNT(*) FROM seasons').fetchone()[0])),
        ('events', str(conn.execute('SELECT COUNT(*) FROM events').fetchone()[0])),
        ('event_occurrences', str(conn.execute('SELECT COUNT(*) FROM event_occurrences').fetchone()[0])),
        ('activities', str(conn.execute('SELECT COUNT(*) FROM activities').fetchone()[0])),
        ('transcript_classification', str(conn.execute('SELECT COUNT(*) FROM transcript_classification').fetchone()[0])),
        ('item_classification', str(conn.execute('SELECT COUNT(*) FROM item_classification').fetchone()[0])),
        ('document_classification', str(conn.execute('SELECT COUNT(*) FROM document_classification').fetchone()[0])),
        ('coverage_notes', str(conn.execute('SELECT COUNT(*) FROM coverage_notes').fetchone()[0])),
        ('speaker_aliases', str(conn.execute('SELECT COUNT(*) FROM speaker_aliases').fetchone()[0])),
        ('caption_provenance', str(conn.execute('SELECT COUNT(*) FROM caption_provenance').fetchone()[0])),
    ]:
        conn.execute('INSERT OR REPLACE INTO meta (key,value) VALUES (?,?)', (k, v))

    conn.commit()
    # Ship a single-file artifact: checkpoint and leave WAL mode behind
    conn.execute('PRAGMA journal_mode=DELETE')
    conn.execute('VACUUM')
    conn.close()
    print(f'database written: {DB_PATH}')

if __name__ == '__main__':
    migrate()
