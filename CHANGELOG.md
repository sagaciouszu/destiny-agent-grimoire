# Changelog

## Session: Agent Compendium & Indexing (2026-11-01)

### Added
- `compendium/` directory: agent-optimized character line index
  - `compendium/index.md` - character index (18 major + 11 minor, 1070 lines)
  - `compendium/characters/<slug>.md` - 19 per-character dialogue files with verified lines and source transcripts
  - `compendium/characters/minor.md` - characters with fewer than 5 lines
- `destiny-1/` directory: Destiny 1 grimoire (in progress)
  - `destiny-1/README.md` - ingestion status and plan
  - `destiny-1/index.md` - ingested card index (10 cards)
  - `destiny-1/cards/*.md` - 10 ingested grimoire cards
- `scripts/ingest-grimoire.py` - fetch and format grimoire cards from Ishtar Collective
- `tests/compendium-check.sh` - agnostic compendium integrity check
- `tests/README.md` - test categorization (archive-agnostic vs agent-integration)
- `skills/destiny-grimoire/SKILL.md` - agent skill connecting to the grimoire
- `CHANGELOG.md` - this file

### Changed
- `index.md` - added Compendium and Destiny 1 sections; updated progress line
- `README.md` - added compendium/destiny-1/scripts to structure; updated usage and progress
- `tests/ci-checks.py` - emdash check skips verbatim source dirs; gitignored/headers checks adapted for grimoire layout

### Removed
- (none)

### Notes
- Destiny 1 full ingestion (~4000+ cards) is pending; 10-card sample ingested.
- No em-dashes in agent-facing files; verbatim lore source exempt.
- No push performed (per instruction).
