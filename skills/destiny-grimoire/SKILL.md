---
name: destiny-grimoire
description: 'Query the Destiny Agent Grimoire for verified Destiny 2 lore, character dialogue, books, and transcripts. Use when an agent needs Destiny lore, character quotes, faction info, or transcript references. Triggers: destiny, lore, grimoire, character lines, transcript, book, quote, faction, location.'
license: MIT
metadata:
  tags: "Destiny, Lore, Grimoire, Characters, Transcripts, Books"
  category: "reference"
---

# Destiny Agent Grimoire

Agent-optimized archive of Destiny 2 lore (110 books, 68 transcripts, 473 verified Drifter lines, 1070 indexed character lines). Use this to pull verified lore on demand without scanning the full corpus.

## Location

- Repo root: `~/Work/destiny-agent-grimoire/` (or wherever cloned)
- Symlink in how-to-drift: `lore/` -> `~/Work/destiny-agent-grimoire/`

## Structure

- `index.md` - Master book list with ingestion status (pending/done/partial) and compendium/destiny-1 sections.
- `books/<slug>.md` - Full text of each book, entries as `##` sections.
- `transcripts/<slug>.md` - Quest dialogue transcripts.
- `compendium/index.md` - Character line index (18 major + 11 minor characters).
- `compendium/characters/<slug>.md` - Per-character dialogue lines with source transcript.
- `destiny-1/README.md` - Destiny 1 grimoire (pending ingestion).
- `tests/` - Validation scripts (archive-agnostic + agent-integration).

## How to query

### Character dialogue
1. Open `compendium/index.md` to find the character and line count.
2. Load `compendium/characters/<slug>.md` for that character's verified lines.

### Book lore
1. Check `index.md` for the book slug and status.
2. Read `books/<slug>.md`.

### Destiny 1 grimoire
1. Look up slug in `destiny-1/index.json` (O(1)) or `destiny-1/index.md`.
2. Read `destiny-1/cards/<slug>.md`.
3. Keyword search: `grep -rli "keyword" destiny-1/cards/`.

### Character interactions
1. Look up in `interactions/index.json` (filter by speaker/keyword).
2. Quote field contains the full dialogue.

### Items / Records
- `items/README.md` and `records/README.md` document pending ingestion.

### Transcript dialogue
1. Check `transcripts/index.md` (6-dimensional index: by arc, beat, character, release, topic, source).
2. Read `transcripts/<slug>.md`.

### Quote verification
- All quotes in agent files are verified against `transcripts/*.md` (473 Drifter lines) + `books/*.md`.
- Run `tests/drifter-quote-verify.sh` to re-verify.

## Rules

- Only use verified quotes. Unverified strings must be unquoted.
- Lore books are verbatim source text; do not paraphrase as quotes.
- Destiny 1 content is not yet ingested; treat as unavailable.
- Keep queries scoped: load only the file you need to save tokens.

## Sources

All content from https://www.ishtar-collective.net (Ishtar Collective). Fan-made, not affiliated with Bungie.
