#!/usr/bin/env python3
"""Migrate markdown + JSONL sources into SQLite database."""
import os, re, json, glob, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy  # noqa: E402
SCHEMA_VERSION = taxonomy.SCHEMA_VERSION
DB_PATH = os.path.join(ROOT, 'db', 'grimoire.db')
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

def norm_text(s):
    """Normalize text for fast substring matching."""
    s = s.lower()
    s = s.replace('…','...').replace('’',"'").replace('—','-').replace('–','-')
    s = re.sub(r'[^a-z0-9 ]+',' ',s)
    s = re.sub(r'\s+',' ',s)
    return s.strip()

def migrate():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
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
        for ln in lines[:20]:
            if ln.startswith('- Release:'):
                release = ln.replace('- Release:','').strip()
            elif ln.startswith('- Characters:'):
                characters = ln.replace('- Characters:','').strip()
            elif ln.startswith('- Arc:'):
                arc = ln.replace('- Arc:','').strip()
        cur = conn.execute(
            'INSERT INTO transcripts (slug,title,release,characters,arc,source_url) VALUES (?,?,?,?,?,?)',
            (slug, title, release, characters, arc, f'https://www.ishtar-collective.net/transcripts/{slug}'))
        tid = cur.lastrowid
        t_count += 1
        seq = 0
        # Audio-quoted line format: '- "quote text"' (no *Speaker:* wrapper)
        is_quoted_file = slug.startswith(('ingame-quotes-', 'youtube-', 'weblore-'))
        if slug.startswith('weblore'):
            print(f'  DEBUG: {slug} is_quoted={is_quoted_file}, line_count={len(lines)}')
        for ln in lines:
            if is_quoted_file:
                m = re.match(r'^-?\s*"(.+?)"\s*(?:(?:-|\u2014)\s*\w.*\s*)?$', ln.strip())
                if m:
                    line = m.group(1).strip()
                    conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir) VALUES (?,?,?,?,?,0)',
                        (tid, seq, 'Drifter', line, norm_text(line)))
                    seq += 1
                    tl_count += 1
                continue
            sp, line = parse_speaker_line(ln)
            if sp and line:
                conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir) VALUES (?,?,?,?,?,0)',
                    (tid, seq, sp, line, norm_text(line)))
                seq += 1
                tl_count += 1
            elif not is_quoted_file and len(ln.strip()) > 20 and not ln.startswith('#') and not ln.startswith('-'):
                # Stage direction / narration line
                conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,norm_line,is_stage_dir) VALUES (?,?,?,?,?,1)',
                    (tid, seq, 'Narration', ln.strip(), norm_text(ln.strip())))
                seq += 1
                tl_count += 1
    print(f'transcripts: {t_count}, lines: {tl_count}')

    # Web transcript pages (archive/data/transcripts_web.jsonl, scraped from Ishtar)
    # Junk speakers are footer "related content" blocks, not dialogue.
    web_jsonl = os.path.join(ROOT, 'archive', 'data', 'transcripts_web.jsonl')
    if os.path.exists(web_jsonl):
        import html as html_mod
        JUNK_SPEAKERS = {'Category', 'Quest', 'Ghost Scan', 'Sources', 'Note', 'Dialogue Option for the Field Assignment'}
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
            cur = conn.execute('INSERT INTO transcripts (slug,title,release,characters,arc,source_url) VALUES (?,?,?,?,?,?)',
                (slug, d.get('title', ''), '', '', '', d.get('source_url', '')))
            tid = cur.lastrowid
            w_count += 1
            seen_page = set()
            seq = 0
            for line in d.get('lines', []):
                sp = line.get('speaker', '')
                txt = deep_unescape(line.get('text', '')).strip()
                # YouTube chapter markers parse as speaker lines:
                # "Cutscene begins at 01:49 and ends at 4:59"
                if re.match(r'^Cutscene (begins|starts) at', sp):
                    continue
                if sp in JUNK_SPEAKERS or not txt:
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
            cur = conn.execute('INSERT INTO transcripts (slug,title,release,characters,arc,source_url) VALUES (?,?,?,?,?,?)',
                (slug, d.get('title', ''), 'Cutscene', '', '', d.get('source_url', '')))
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

    # Build FTS index (global rowid sequence)
    print('building FTS index...')
    fts_id = 0
    def add_fts(title, text, speaker='', body='', source='', source_slug=''):
        nonlocal fts_id
        fts_id += 1
        conn.execute('INSERT INTO fts (rowid,title,text,speaker,body,source,source_slug) VALUES (?,?,?,?,?,?,?)',
            (fts_id, title, text or '', speaker, body or '', source, source_slug))
    for bid, slug, title in conn.execute('SELECT id,slug,title FROM books').fetchall():
        for eid, etitle, ebody in conn.execute('SELECT id,title,body FROM book_entries WHERE book_id=?', (bid,)).fetchall():
            add_fts(f'{title}: {etitle}', ebody, source='book_entry', source_slug=slug)
    for tid, slug, title in conn.execute('SELECT id,slug,title FROM transcripts').fetchall():
        for tlid, sp, line in conn.execute('SELECT id,speaker,line FROM transcript_lines WHERE transcript_id=?', (tid,)).fetchall():
            add_fts(title, line, sp, source='transcript_line', source_slug=slug)
    for gid, slug, title, body in conn.execute('SELECT id,slug,title,body FROM grimoire_cards').fetchall():
        add_fts(title, body, source='grimoire_card', source_slug=slug)
    for iid, slug, title, speaker, text in conn.execute('SELECT id,slug,title,speaker,text FROM interactions').fetchall():
        add_fts(title, text, speaker, source='interaction', source_slug=slug)
    for iid, slug, title, text in conn.execute('SELECT id,slug,title,text FROM items').fetchall():
        if text:  # stat-only items have no searchable text
            add_fts(title, text, source='item', source_slug=slug)
    for rid, slug, title, body in conn.execute('SELECT id,slug,title,body FROM records').fetchall():
        add_fts(title, body, source='record', source_slug=slug)
    print(f'fts entries: {fts_id}')

    # Verification index: normalized text with provenance (documents only)
    print('building verification index...')
    for sql in (
        "INSERT INTO verify_fts(norm, source, slug, speaker) "
        "SELECT tl.norm_line, 'transcript', t.slug, tl.speaker "
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
    t_count = conn.execute('SELECT COUNT(*) FROM item_title_fts').fetchone()[0]
    print(f'item title entries: {t_count}')

    # Meta
    for k, v in [
        ('version',SCHEMA_VERSION),
        ('last_updated','2026-11-04'),
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
