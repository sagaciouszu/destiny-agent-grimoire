PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT,
    entry_count INTEGER DEFAULT 0,
    timeline TEXT,
    timeline_basis TEXT
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
    source_url TEXT,
    source_tier TEXT,
    timeline TEXT,               -- in-universe story chapter slug (timeline_chapters)
    timeline_basis TEXT,          -- classification | release_name | scene_flashback
    lang TEXT NOT NULL DEFAULT 'en'  -- caption/subtitle language; every row defaults
                                    -- to English so a future language drop adds
                                    -- data rows only, never a schema change
);
CREATE INDEX IF NOT EXISTS idx_transcripts_slug ON transcripts(slug);

CREATE TABLE IF NOT EXISTS transcript_lines (
    id INTEGER PRIMARY KEY,
    transcript_id INTEGER NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    seq INTEGER,
    speaker TEXT,
    line TEXT,
    norm_line TEXT,
    is_stage_dir INTEGER DEFAULT 0,
    section TEXT,
    is_optional INTEGER DEFAULT 0,
    class_tag TEXT,
    speaker_source TEXT
);
CREATE INDEX IF NOT EXISTS idx_tl_transcript ON transcript_lines(transcript_id);
CREATE INDEX IF NOT EXISTS idx_tl_speaker ON transcript_lines(speaker);
CREATE INDEX IF NOT EXISTS idx_tl_norm ON transcript_lines(norm_line);

-- Game-file caption provenance. Every caption line keeps its StringReference
-- hash and package origin so a canonical line traces back to the build it
-- came from. Lives outside the canon columns of transcript_lines.
CREATE TABLE IF NOT EXISTS caption_provenance (
    line_id INTEGER PRIMARY KEY REFERENCES transcript_lines(id) ON DELETE CASCADE,
    hash INTEGER,               -- StringReference hash; NULL for unlinked banks
    kind TEXT,                  -- table kind: cinematic | dialogue | callout | activity_narration
    source_pkg TEXT,            -- package base, e.g. w64_globals_01cf
    source_entry INTEGER,       -- StringReference entry index
    bank_entry INTEGER          -- StringBank entry index
);
CREATE INDEX IF NOT EXISTS idx_cp_kind ON caption_provenance(kind);
CREATE INDEX IF NOT EXISTS idx_cp_pkg ON caption_provenance(source_pkg);
CREATE INDEX IF NOT EXISTS idx_cp_hash ON caption_provenance(hash);

CREATE TABLE IF NOT EXISTS grimoire_cards (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT,
    body TEXT,
    norm_body TEXT,
    game TEXT DEFAULT 'Destiny 1',
    source_url TEXT,
    timeline TEXT,
    timeline_basis TEXT
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
    source_url TEXT,
    timeline TEXT,
    timeline_basis TEXT
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
    source_url TEXT,
    timeline TEXT,
    timeline_basis TEXT
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
    source_url TEXT,
    timeline TEXT,
    timeline_basis TEXT
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
    source_slug TEXT,
    timeline TEXT                -- inherited from the source transcript
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

-- In-universe Destiny timeline: story chapters (rank = chronological order).
-- Rows carry the chapter slug in their `timeline` column; join this table for
-- rank/label. NULL timeline = unknown position (honest gap, not a default).
CREATE TABLE IF NOT EXISTS timeline_chapters (
    rank INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    title, text, speaker, body, source,
    source_slug UNINDEXED,
    class_tag UNINDEXED,
    timeline UNINDEXED,
    lang UNINDEXED,
    tokenize='porter unicode61'
);

-- Activity / season / event taxonomy lives in db/taxonomy.py (single source).
-- migrate.py calls taxonomy.ensure_schema() so fresh builds get the tables
-- without duplicating the DDL here.

-- Fast quote verification: normalized text with provenance (documents only)
CREATE VIRTUAL TABLE IF NOT EXISTS verify_fts USING fts5(
    norm, source UNINDEXED, slug UNINDEXED, speaker UNINDEXED,
    tokenize='porter unicode61'
);

-- Item title lookup for find_item (titles only; lore text stays in fts)
CREATE TABLE IF NOT EXISTS lore_entries (
    id INTEGER PRIMARY KEY,
    hash INTEGER UNIQUE NOT NULL,
    title TEXT,
    subtitle TEXT,
    body TEXT,
    norm_body TEXT,
    source TEXT DEFAULT 'bungie_manifest',
    source_url TEXT,
    is_duplicate INTEGER DEFAULT 0,
    duplicate_of TEXT
);
CREATE INDEX IF NOT EXISTS idx_lore_norm ON lore_entries(norm_body);

CREATE TABLE IF NOT EXISTS lore_entry_items (
    lore_hash INTEGER NOT NULL,
    item_title TEXT NOT NULL,
    PRIMARY KEY (lore_hash, item_title)
);
CREATE INDEX IF NOT EXISTS idx_lore_items_title ON lore_entry_items(item_title);

CREATE VIRTUAL TABLE IF NOT EXISTS item_title_fts USING fts5(
    title, slug UNINDEXED, item_type UNINDEXED, release UNINDEXED,
    tokenize='unicode61'
);
