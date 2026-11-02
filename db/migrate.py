#!/usr/bin/env python3
"""Migrate markdown + JSONL sources into SQLite database."""
import os, re, json, glob, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

def parse_speaker_line(ln):
    m = re.match(r'^\*(?:The )?(.+?):\*\s*(.*)$', ln.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None

def migrate():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(open(SCHEMA).read())

    # Books
    books = glob.glob(os.path.join(ROOT, 'source', 'books', '*.md'))
    book_count = 0
    entry_count = 0
    for path in books:
        slug = os.path.basename(path)[:-3]
        title, sections, _ = parse_md_sections(path)
        cur = conn.execute('INSERT INTO books (slug,title,source_url,entry_count) VALUES (?,?,?,?)',
            (slug, title, f'https://www.ishtar-collective.net/categories/{slug}', len(sections)))
        bid = cur.lastrowid
        book_count += 1
        for i, (st, sb) in enumerate(sections):
            conn.execute('INSERT INTO book_entries (book_id,title,body,seq) VALUES (?,?,?,?)',
                (bid, st, sb, i))
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
        for ln in lines:
            sp, line = parse_speaker_line(ln)
            if sp and line:
                conn.execute('INSERT INTO transcript_lines (transcript_id,seq,speaker,line,is_stage_dir) VALUES (?,?,?,?,0)',
                    (tid, seq, sp, line))
                seq += 1
                tl_count += 1
    print(f'transcripts: {t_count}, lines: {tl_count}')

    # Grimoire cards
    cards = glob.glob(os.path.join(ROOT, 'source', 'cards', '*.md'))
    g_count = 0
    for path in cards:
        slug = os.path.basename(path)[:-3]
        text = open(path, encoding='utf-8', errors='ignore').read()
        lines = text.split('\n')
        title = lines[0].lstrip('# ').strip() if lines else ''
        body = '\n'.join(lines[2:]).strip()
        conn.execute('INSERT OR IGNORE INTO grimoire_cards (slug,title,body,game) VALUES (?,?,?,?)',
            (slug, title, body, 'Destiny 1'))
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
                conn.execute('INSERT OR IGNORE INTO interactions (slug,title,speaker,text,release,source_url) VALUES (?,?,?,?,?,?)',
                    (slug, d.get('title',''), d.get('speaker',''), d.get('text',''), d.get('release',''), d.get('url','')))
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
                conn.execute('INSERT OR IGNORE INTO items (slug,title,text,release,item_type,source_url) VALUES (?,?,?,?,?,?)',
                    (slug, d.get('title',''), d.get('text',''), d.get('release',''), d.get('type',''), d.get('url','')))
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
                conn.execute('INSERT OR IGNORE INTO records (slug,title,body,release,source_url) VALUES (?,?,?,?,?)',
                    (d.get('slug',''), d.get('title',''), d.get('body',''), d.get('release',''), d.get('url','')))
                r_count += 1
            except: pass
    else:
        idx_path = os.path.join(ROOT, 'records', 'records-index.json')
        if os.path.exists(idx_path):
            idx = json.load(open(idx_path))
            for e in idx.get('entries', []):
                slug = e.get('slug','')
                body_path = os.path.join(ROOT, 'source', 'records', slug+'.md')
                body = ''
                if os.path.exists(body_path):
                    body = open(body_path, encoding='utf-8').read()
                conn.execute('INSERT OR IGNORE INTO records (slug,title,body,release,source_url) VALUES (?,?,?,?,?)',
                    (slug, e.get('title',''), body, e.get('release',''), f'https://www.ishtar-collective.net/records/{slug}'))
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
            for m in re.finditer(r'^- "(.+?)"\s*-\s*(\S+)', text, re.M):
                text_line = m.group(1)
                src = m.group(2)
                conn.execute('INSERT INTO character_lines (character_id,text,source_type,source_slug) VALUES (?,?,?,?)',
                    (cid, text_line, 'transcript', src))
                cl_count += 1
    print(f'characters: {c_count}, lines: {cl_count}')

    # Build FTS index (global rowid sequence)
    print('building FTS index...')
    fts_id = 0
    def add_fts(title, text, speaker='', body=''):
        nonlocal fts_id
        fts_id += 1
        conn.execute('INSERT INTO fts (rowid,title,text,speaker,body) VALUES (?,?,?,?,?)',
            (fts_id, title, text or '', speaker, body or ''))
    for bid, slug, title in conn.execute('SELECT id,slug,title FROM books').fetchall():
        for eid, etitle, ebody in conn.execute('SELECT id,title,body FROM book_entries WHERE book_id=?', (bid,)).fetchall():
            add_fts(f'{title}: {etitle}', ebody)
    for tid, slug, title in conn.execute('SELECT id,slug,title FROM transcripts').fetchall():
        for tlid, sp, line in conn.execute('SELECT id,speaker,line FROM transcript_lines WHERE transcript_id=?', (tid,)).fetchall():
            add_fts(title, line, sp)
    for gid, slug, title, body in conn.execute('SELECT id,slug,title,body FROM grimoire_cards').fetchall():
        add_fts(title, body)
    for iid, slug, title, speaker, text in conn.execute('SELECT id,slug,title,speaker,text FROM interactions').fetchall():
        add_fts(title, text, speaker)
    for iid, slug, title, text in conn.execute('SELECT id,slug,title,text FROM items').fetchall():
        add_fts(title, text)
    for rid, slug, title, body in conn.execute('SELECT id,slug,title,body FROM records').fetchall():
        add_fts(title, body)
    print(f'fts entries: {fts_id}')

    # Meta
    for k, v in [
        ('version','1.0.0'),
        ('last_updated','2026-11-02'),
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
    ]:
        conn.execute('INSERT OR REPLACE INTO meta (key,value) VALUES (?,?)', (k, v))

    conn.commit()
    conn.execute('VACUUM')
    conn.close()
    print(f'database written: {DB_PATH}')

if __name__ == '__main__':
    migrate()
