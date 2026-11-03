PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT,
    entry_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_books_slug ON books(slug);

CREATE TABLE IF NOT EXISTS book_entries (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    title TEXT,
    body TEXT,
    norm_text TEXT,
    seq INTEGER
);
CREATE INDEX IF NOT EXISTS idx_book_entries_book ON book_entries(book_id);
CREATE INDEX IF NOT EXISTS idx_book_entries_norm ON book_entries(norm_text);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT,
    release TEXT,
    characters TEXT,
    arc TEXT,
    source_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_transcripts_slug ON transcripts(slug);

CREATE TABLE IF NOT EXISTS transcript_lines (
    id INTEGER PRIMARY KEY,
    transcript_id INTEGER NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    seq INTEGER,
    speaker TEXT,
    line TEXT,
    norm_line TEXT,
    is_stage_dir INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tl_transcript ON transcript_lines(transcript_id);
CREATE INDEX IF NOT EXISTS idx_tl_speaker ON transcript_lines(speaker);
CREATE INDEX IF NOT EXISTS idx_tl_norm ON transcript_lines(norm_line);

CREATE TABLE IF NOT EXISTS grimoire_cards (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT,
    body TEXT,
    norm_body TEXT,
    game TEXT DEFAULT 'Destiny 1',
    source_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_gc_slug ON grimoire_cards(slug);
CREATE INDEX IF NOT EXISTS idx_gc_norm ON grimoire_cards(norm_body);

CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT,
    speaker TEXT,
    text TEXT,
    norm_text TEXT,
    release TEXT,
    source_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_int_slug ON interactions(slug);
CREATE INDEX IF NOT EXISTS idx_int_speaker ON interactions(speaker);
CREATE INDEX IF NOT EXISTS idx_int_norm ON interactions(norm_text);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT,
    text TEXT,
    norm_text TEXT,
    release TEXT,
    item_type TEXT,
    source_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_slug ON items(slug);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type);
CREATE INDEX IF NOT EXISTS idx_items_norm ON items(norm_text);

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT,
    body TEXT,
    norm_body TEXT,
    release TEXT,
    source_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_records_slug ON records(slug);
CREATE INDEX IF NOT EXISTS idx_records_norm ON records(norm_body);

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_characters_slug ON characters(slug);

CREATE TABLE IF NOT EXISTS character_lines (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    norm_text TEXT,
    source_type TEXT,
    source_slug TEXT
);
CREATE INDEX IF NOT EXISTS idx_cl_character ON character_lines(character_id);
CREATE INDEX IF NOT EXISTS idx_cl_source ON character_lines(source_type, source_slug);
CREATE INDEX IF NOT EXISTS idx_cl_norm ON character_lines(norm_text);

CREATE TABLE IF NOT EXISTS speaker_aliases (
    alias TEXT PRIMARY KEY,
    canonical TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_speakers AS
    SELECT speaker, COUNT(*) AS lines
    FROM transcript_lines
    WHERE speaker NOT IN ('Narration', 'Cutscene')
    GROUP BY speaker;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    title, text, speaker, body, source,
    tokenize='porter unicode61'
);
