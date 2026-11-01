# Destiny Agent Grimoire

<p align="center">
  <img src='https://img.shields.io/github/v/tag/sagaciouszu/destiny-agent-grimoire?label=version&color=blue' alt='Version'/>
  <img src='https://github.com/sagaciouszu/destiny-agent-grimoire/actions/workflows/ci.yml/badge.svg' alt='CI'/>
  <img src='https://img.shields.io/badge/books-110-orange' alt='Books'/>
  <img src='https://img.shields.io/badge/transcripts-68-orange' alt='Transcripts'/>
  <img src='https://img.shields.io/badge/quotes-473%20verified-orange' alt='Quotes'/>
  <img src='https://img.shields.io/badge/Made%20with-Motes-00FF00' alt='Made with Motes'/>
  <img src='https://img.shields.io/badge/Made%20with-Parts%20of%20Ghosts-FFFFFF' alt='Made with Parts of Ghosts'/>
</p>

<p align="center">
  <img src="header.png" alt="Destiny Agent Grimoire - Your Ghost Is Not An Agent" width="100%"/>
</p>

**Version:** 0.2.3 | **Status:** Development

> ⚠️ **WARNING:** This repository is under heavy development while the knowledge base is being constructed. Expect frequent changes, incomplete data, and shifting structure. The author's prowess is not to be trusted with anything important. Use at your own risk.

A shared, indexed repository of Destiny 2 lore ingested from the Ishtar Collective.
Any agent (Drifter persona, lore research, etc.) may reference these files at will.

## Structure

- `index.md` - Master book list with ingestion status (pending/done/partial).
- `books/<slug>.md` - Full text of each ingested book, entries as `##` sections.
- `transcripts/<slug>.md` - Transcripts (quest dialogue) as ingested.
- `compendium/` - Agent-optimized character line index (per-character files, load only what you need).
- `destiny-1/` - Destiny 1 grimoire (in progress).
- `tests/` - Validation and verification scripts (29 scripts).
- `drifter-master-audit.sh` - Unified audit runner (stays at root).
- `scripts/ingest-grimoire.py` - Ingest Destiny 1 grimoire cards from Ishtar Collective.

## How to use

1. Check `index.md` for a book's status and slug.
2. Read `books/<slug>.md` for the full lore text.
3. Entries within a book are separated by `## Entry Title` headers.
4. For character dialogue, load `compendium/characters/<slug>.md` instead of scanning all transcripts.
5. Destiny 1 content is pending; see `destiny-1/README.md`.

## Ingestion rules

- Only lore body text is kept - site navigation, headers, footers, category lists, timeline widgets, and "Discuss this transcript" links are stripped.
- If an entry cannot be fetched, the book is marked `partial` with a note; nothing is invented.
- Capitalization matters: "Guardian" (capitalized) generally refers to the player character.

## Source & Attributions

All content sourced from https://www.ishtar-collective.net (Ishtar Collective).
Book list mirrored from https://www.ishtar-collective.net/books.

Fan-made collection. Not affiliated with or endorsed by Bungie.

- **Destiny 2** - © Bungie, Inc. All lore, characters, locations are Bungie's property.
- **Ishtar Collective** (https://www.ishtar-collective.net) - Primary source for all ingested lore text.
- **Destiny Lore Vault** (YouTube) - Audio recordings of key transcripts.

All content sourced from publicly available Destiny 2 lore. No original creative content is claimed.

## Progress

110 / 110 books ingested (Destiny 2). 68 transcripts ingested. Compendium: 18 major + 11 minor characters, 1070 lines. Destiny 1: 1789 / ~4000+ cards ingested (pages 1-90).
Last scrape: 2026-10-30. Content through Renegades (Dec 2025).

## Audit Commands
- `bash tests/validate.sh` - consistency check (quotes, links, index)
- `bash tests/drifter-test-suite.sh` - voice validation (19 scenarios)
- `bash tests/drifter-module-test.sh` - module checks (201 checks)
- `bash drifter-master-audit.sh` - unified audit (17 suites)
- `bash tests/drifter-quote-verify.sh` - quote verification
- `bash tests/drifter-ci.sh` - full CI pipeline (25 checks)
- `bash tests/lore-integrity.sh` - archive integrity (8 checks)
- `bash tests/lore-quote-count.sh` - quote count (473 lines)
- `bash tests/lore-format.sh` - transcript format (68/68)
