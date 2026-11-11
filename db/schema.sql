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

-- Game-file caption provenance. Every caption line keeps its build origin so a
-- canonical line traces back to the build it came from. Lives outside the
-- canon columns of transcript_lines.
CREATE TABLE IF NOT EXISTS caption_provenance (
    line_id INTEGER PRIMARY KEY REFERENCES transcript_lines(id) ON DELETE CASCADE,
    hash INTEGER,               -- StringReference hash; NULL where the build has none
    kind TEXT,                  -- table kind: cinematic | dialogue | callout | activity_narration | narration | objective
    source_pkg TEXT,            -- package base, e.g. w64_globals_01cf
    source_entry INTEGER,       -- StringReference entry index
    bank_entry INTEGER,         -- StringBank entry index
    record_index INTEGER,       -- line's slot in the bank entry; NULL for hash-keyed tiers
    record_part INTEGER,        -- paragraph within a multi-paragraph slot; NULL when unsplit
    source_build TEXT NOT NULL DEFAULT 'sunrise-pre-bl'  -- builds.build_id; NULL never
);
CREATE INDEX IF NOT EXISTS idx_cp_kind ON caption_provenance(kind);
CREATE INDEX IF NOT EXISTS idx_cp_pkg ON caption_provenance(source_pkg);
CREATE INDEX IF NOT EXISTS idx_cp_hash ON caption_provenance(hash);

-- Every observation of a caption line, including the ones that lose the
-- one-row-per-line race in caption_provenance. `caption_provenance` stays the
-- current/fast index; this is the observation log. Identity is one row per
-- processed JSONL line: the source record slug plus the line's ordinal in that
-- record. A physical-slot key would collapse genuinely distinct sunrise lines
-- that share a bank entry and carry no record index (measured: 1,070 lines).
CREATE TABLE IF NOT EXISTS caption_sightings (
    line_id INTEGER NOT NULL REFERENCES transcript_lines(id) ON DELETE CASCADE,
    source_build TEXT NOT NULL REFERENCES builds(build_id),
    source_slug TEXT NOT NULL,    -- caption record slug (unique across both files)
    line_ord INTEGER NOT NULL,    -- index in the record's `lines` array
    source_pkg TEXT,              -- package base, e.g. w64_sr_globals_0294
    source_entry INTEGER,         -- StringReference entry index
    bank_entry INTEGER,           -- StringBank entry index
    record_index INTEGER,         -- slot in the bank entry
    record_part INTEGER,          -- paragraph within a multi-paragraph slot
    kind TEXT,                    -- table kind at this sighting
    hash INTEGER,                 -- StringReference hash when the build has one
    captured_at TEXT NOT NULL,    -- builds.captured_at for this build
    PRIMARY KEY (line_id, source_build, source_slug, line_ord)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_cs_build ON caption_sightings(source_build);
CREATE INDEX IF NOT EXISTS idx_cs_slug ON caption_sightings(source_slug);

-- Build registry: one row per game build / manifest snapshot the corpus was
-- built on. Caption rows in caption_provenance.source_build name a row of
-- this table. Every future ingestion run registers itself here (STANDARDS.md,
-- Corpus scope). Counts below are point-in-time snapshots, refreshed by the
-- release that re-ingests a tier.
CREATE TABLE IF NOT EXISTS builds (
    build_id      TEXT PRIMARY KEY,   -- 'sunrise-pre-bl', 'build-25932352', ...
    label         TEXT NOT NULL,      -- human-facing name
    kind          TEXT NOT NULL CHECK (kind IN ('game_build','web_capture','manifest')),
    version       TEXT NOT NULL,      -- Bungie stamp / 'n/a' for web captures
    source        TEXT NOT NULL,      -- install path or author domain
    captured_at   TEXT NOT NULL,      -- ISO date of extraction or capture snapshot; 'pending' if not run yet
    package_count INTEGER,            -- NULL for web captures / pending
    byte_count    INTEGER,            -- NULL for web captures / pending
    notes         TEXT NOT NULL DEFAULT ''
);

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

CREATE TABLE IF NOT EXISTS speaker_aliases (
    alias TEXT PRIMARY KEY,
    canonical TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_speakers AS
    SELECT speaker, COUNT(*) AS lines
    FROM transcript_lines
    WHERE speaker NOT IN ('Narration', 'Cutscene')
    GROUP BY speaker;

-- Canon speakers: at least one persona-canon line (non-stage, non-optional,
-- non-caption). v_speakers stays the discovery view; this one is the curated
-- membership list. Raw speaker strings are kept, including qualifiers.
CREATE VIEW IF NOT EXISTS v_canon_speakers AS
    SELECT tl.speaker AS speaker,
           COUNT(*) AS lines,
           COUNT(DISTINCT tl.transcript_id) AS transcripts
    FROM transcript_lines tl
    JOIN transcripts t ON t.id = tl.transcript_id
    WHERE tl.speaker IS NOT NULL
      AND tl.speaker NOT IN ('Narration', 'Cutscene')
      AND tl.is_stage_dir = 0
      AND tl.is_optional = 0
      AND COALESCE(t.source_tier, '') != 'game_caption'
    GROUP BY tl.speaker;

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
    title, text, speaker, body, source, norm,
    source_slug UNINDEXED,
    class_tag UNINDEXED,
    timeline UNINDEXED,
    lang UNINDEXED,
    tokenize='porter unicode61'
);

-- Activity / season / event taxonomy lives in db/taxonomy.py (single source).
-- migrate.py calls taxonomy.ensure_schema() so fresh builds get the tables
-- without duplicating the DDL here.

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

-- Entity web (additive; see db/build_entity_web.py and RELEASE v0.33.0).
-- Books/lore/transcripts are read-only source of truth: these tables only
-- reference them by slug/hash ref strings, never by constraint, so no
-- existing row is ever rewritten.
CREATE TABLE IF NOT EXISTS entities (
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
CREATE INDEX IF NOT EXISTS idx_entities_kind ON entities(kind);

CREATE TABLE IF NOT EXISTS entity_aliases (
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
CREATE INDEX IF NOT EXISTS idx_entity_aliases_entity ON entity_aliases(entity_id);

CREATE TABLE IF NOT EXISTS entity_links (
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
CREATE INDEX IF NOT EXISTS idx_entity_links_entity ON entity_links(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_kind_ref ON entity_links(kind, ref);
CREATE INDEX IF NOT EXISTS idx_entity_links_rank ON entity_links(entity_id, weight DESC);

CREATE TABLE IF NOT EXISTS entity_relations (
    id               INTEGER PRIMARY KEY,
    entity_id        INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation         TEXT NOT NULL CHECK (relation IN ('adjacent_to','related_to')),
    target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    source           TEXT NOT NULL DEFAULT 'owner-ruling-2026-11-09',
    UNIQUE (entity_id, relation, target_entity_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_relations_target ON entity_relations(target_entity_id);

CREATE TABLE IF NOT EXISTS entity_build_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_entity_resolve AS
SELECT e.id AS entity_id, e.canonical, e.kind, e.confidence AS entity_confidence,
       a.alias, a.norm_alias, a.confidence AS alias_confidence,
       a.requires_ctx, a.reviewed, e.norm_key
FROM entity_aliases a JOIN entities e ON e.id = a.entity_id;

CREATE VIEW IF NOT EXISTS v_entity_documents AS
SELECT l.entity_id, e.canonical, e.kind, l.kind AS doc_kind, l.ref,
       l.weight, l.match,
       ROW_NUMBER() OVER (PARTITION BY l.entity_id
                          ORDER BY l.weight DESC, l.ref) AS rank_in_entity
FROM entity_links l JOIN entities e ON e.id = l.entity_id;

CREATE VIEW IF NOT EXISTS v_entity_coverage AS
WITH k AS (
  SELECT e.id, e.kind, COUNT(l.id) AS links, SUM(l.weight) AS weight_sum
  FROM entities e LEFT JOIN entity_links l ON l.entity_id = e.id
  GROUP BY e.id
)
SELECT kind, COUNT(*) AS entities,
       SUM(CASE WHEN links>0 THEN 1 ELSE 0 END) AS entities_with_links,
       SUM(links) AS links, AVG(links) AS avg_links_per_entity
FROM k GROUP BY kind;
