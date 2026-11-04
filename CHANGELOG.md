## v0.21.0 - Activity, season and event taxonomy (2026-11-04)

- Additive taxonomy: `expansions` (18), `seasons` (26), `events` (9),
  `event_occurrences` (72), `activities` (67).
- Classification for every transcript, item, book and record with
  `explicit` / `derived` / `manual` / `unknown` confidence and evidence.
- Official season numbers; episodes 24-26 modelled with `season_type='episode'`
  and act support.
- Rotating events modelled with yearly occurrences: Festival of the Lost,
  The Dawning, Solstice, Guardian Games, Crimson Days, The Revelry,
  Moments of Triumph, Bungie Day, Iron Banner.
- Vaulted flag across seasons, activities and events.
- New discovery: `--activity`, `--season`, `--event`, `--expansion` facets on
  search; `activity`, `event`, `coverage` CLI commands; six new MCP tools.
- Coverage views and `docs/TAXONOMY.md`.

## v0.20.0 - Series, isolation and test ownership (2026-11-03)

- `series/agents.json` drives deployment; agents install as `<id>.md` + `<id>/`.
- Read-only `-consult` subagents; primaries are primary-only; peer reads denied.
- Drifter and Eris suites moved into their repos; the grimoire audit is shared-only (9 suites).
- Input hardening: literal FTS fallback, speaker boundary matching, bidi/control stripping, LIKE escaping.
- CI runs robustness and agent-layout gates with least-privilege permissions.
- OpenClaw parity: one workspace per agent, series blocks, read-only consult wiring.

# Changelog

## v0.19.0 - Compendium and coverage (2026-11-03)

Versioning reset: this line stays below 1.0 until a major milestone.

- compendium adds Ikora Rey and Mara Sov (20 characters, 1,229 quotes)
- 1,003 item types backfilled; remaining blanks are source-optional
- golden voice snapshots, documentation command audit, item audit
- CI workflow active; OpenCode and OpenClaw bindings documented



- item types backfilled from duplicate titles (1,003 rows; 3,634 remain source-blank)
- compendium expanded with Ikora Rey and Mara Sov (20 characters, 1,229 quotes)
- golden voice snapshots for both agents (6 fixed verdicts)
- documentation command audit (180 commands) and copy-safe command forms
- CI active at `.github/workflows/ci.yml`


## v0.18.1 - Character lookup and ranking fixes (2026-11-03)

- exact character resolution (drifter no longer resolves to Blue's Ghost)
- title-boosted relevance with item penalty; --no-rank available
- docs for ranking and offsets

## v0.18.0 - Leaner index and operations tooling (2026-11-03)

- stat-only items excluded from FTS (136,802 -> 120,731 rows)
- schema version file and database gate (1.0.1)
- item provenance audit, retrieval eval, DB/source cross-check
- slim database builder (95 MB), release/backup/sync scripts
- CI workflow for build, conformance, database, interface, retrieval, MCP

## v0.17.1 - Clone-mode quote scan fix (2026-11-03)

- drifter-quote-verify excludes the cloned lore archive (fresh-clone audit 18/18)
- removed an unrelated session note accidentally committed in v1.7.0

## v0.17.0 - Retrieval quality and deeper MCP (2026-11-03)

- retrieval eval harness (15 queries); relevance ordering now default
- item_title_fts index for fast find_item title lookup
- search totals/next_offset; verify_many (20); character_info
- MCP resource templates (book/transcript/character/record) and two prompts
- verification cache for repeated MCP calls
- database 170 MB, 38 checks, interface 29 checks, matrix 141 calls

## v0.16.0 - MCP reading tools and pagination (2026-11-03)

- MCP: book, transcript, find_item and record tools; ten tools total
- Pagination (`offset`) across tools and CLI; book/transcript totals
- Resources: grimoire://books, characters, records, stats
- Read-only/idempotent tool annotations; CLI parity for all reading commands
- Interface 27 checks; MCP matrix 138 calls across ten tools and four resources

## v0.15.0 - Faster verification and hardened delivery (2026-11-03)

- verify_fts index: quote checks ~58 ms -> ~1.4 ms; database 164 MB, reproducible
- onboarding verifies the prebuilt database against release SHA256SUMS
- MCP dependencies hash-locked (`--require-hashes`); stdio-only posture documented
- corrupt/truncated/missing databases fail cleanly; query and quote lengths bounded
- extended regression: robustness, MCP matrix, checksum faults, DB/source cross-check
- seeded runtime memory is owner-only (0600)

## v0.14.0 - MCP adapter and attribution-aware verification (2026-11-03)

- verify gains `--speaker` (attribution) and `--exact` (full line); MCP exposes both
- CLI limits decoupled from MCP: API up to 10,000, MCP clamps to 1-100
- Database ships in `journal_mode=delete`; no WAL/SHM sidecars (36 checks)
- Onboarding: `--mcp` flag and interactive prompt; one install serves both agents
- MCP adapter: `mcp-server/` uses the official SDK (stdio, read-only) to expose
  `search`, `character`, `item`, `verify`, `list_records`, `stats` as typed tools;
  install with `bash mcp-server/install.sh` or `./setup.sh --mcp`
- `db/api.py`: shared importable query layer behind both the CLI and the MCP
  server; CLI output unchanged (23/23 interface checks)
- `tests/mcp-test.py`: tool contract, read-only guard, limit clamping and a real
  stdio handshake; skips without the optional venv

## v0.13.1 - Documentation and verification overhaul (2026-11-02)

- README standard: banner, version, last push, Guardian-first quick start, agent
  contract, layout, verification, troubleshooting; gated by conformance
- Release notes compacted to What's Changed / Verification / Asset, capped at 40 lines
- SOUL, TOOLS, INDEX, IDENTITY and templates share one section order across agents
- New gates: README contract, command targets, agent parity (setup, gitignore,
  document sections, load tiers), release-note shape, tracked symlinks
- New tests: offline onboarding smoke (24 checks), link checker (private-aware),
  README metadata stamper
- Fixed: conformance path resolution through the `lore/` symlink; `orix` -> `oryx`

- Centralized agent testing: Eris suites moved to `tests/` beside the Drifter's;
  one shared `tests/agent-audit.sh` runner and `tests/check-agent-structure.py`
  (dependency resolution, tokens, dashes, INDEX completeness, personal paths)
- Renamed the archive-wide audit to `grimoire-master-audit.sh` (was misnamed
  `eris-master-audit.sh`); `eris-master-audit.sh` now audits the Eris workspace
- Agent repos: no local `tests/`, `lore/` is runtime-only, identical `.gitignore`,
  identical `setup.sh` structure; Drifter 18 suites, Eris 13, archive 11
- INDEX completeness fixed (`core/relationship-evolution.md`), quote index
  regenerated from canon, tracked-symlink gate added

## v0.13.0 - Standards + agent interface v2 (2026-11-02)

- STANDARDS.md: schema contract, naming/canonical speakers, provenance, quote policy, verification gates, connection matrix
- Database to standards: speaker alias canonicalization at migration (0 variants), grimoire_cards.source_url (2889/2889), speaker_aliases table, v_speakers view, capabilities.json manifest
- Agent interface v2: snippet-first search (with FTS source column fixing the --type bug), --json everywhere, verify (quote safety), list discovery, character --about/--all
- Data integrity: entity leakage eliminated (deep unescape), compendium multi-quote parser (15 broken provenance -> 0, +135 quotes), book slug/URL alignment (108 dead links fixed), visit-8 rebuild, filename/source gates
- Verification: conformance.py (all 3 repos), source-overlap + speaker-audit gated into the master audit, query-interface-test (23 checks); test-db 35 checks
- Cutscene corpus: 31 videos, 47,576 lines (auto-generated captions, quality-gated)
- Counts: 1229 transcripts, 71,221 lines, FTS 136,802, 1,189 character quotes

## v0.12.0 - Web transcripts + cutscenes + quote-verify hardening (2026-11-02)

### Packaging

- `db/grimoire.db` is now a build artifact: stripped from git (exceeded GitHub's 100MB limit), gitignored, rebuilt via `python3 db/migrate.py`, prebuilt copy attached to the release
- Cutscene caption verification suite (`tests/cutscene-verify.sh`, 8-gram shingles): 7/7 master-audit suites
- Legacy ingest scripts removed (superseded by `archive/` scrapers); remaining scripts use repo-relative paths
- Preload checks print bootstrap guidance when the database is missing (no dead ends for agents)
- MIT LICENSE added to agent repositories (matching their stated badges)

### Coverage

- Scraped all 1130 additional Ishtar transcript pages (68 -> 1198 transcripts), incl. quest-step dialogue for every expansion
- Added 31 cutscene compilation transcripts (D1 + D2, captions only, no video download) with unique-match speaker attribution (455 lines)
- Captions are YouTube auto-generated (no manual tracks exist); cutscene-verify gates corroboration, encoding, cross-video consistency and attribution
- Database: 1222 transcripts, 64,034 transcript lines, 129,615 FTS entries

### Tests

- `drifter-quote-verify.sh`: sentence-level matching for dropped attributions; canon fragments split from raw lines (norm strips periods)
- `drifter-voice-scorer.py`: DB-backed corpus (1001 Drifter lines)
- `ci-checks.py`: source-lore exemptions, RELEASE.md header exemption
- `tests/lore-format.sh`: path fixed for `source/transcripts/` reorganization

## v0.11.0 - Ishtar coverage complete + source trim (2026-11-02)

### Coverage

- Verified full Ishtar Collective coverage: 0 missing item slugs, all 135 interaction pages, all 110 books, 2889 D1 cards, 71 records

### Cleanup

- Removed redundant `source/items/` and `source/interactions/` markdown (items/interactions ingest from `archive/data/*.jsonl`)
- `source/` now contains exactly what `db/migrate.py` consumes: books, transcripts, cards, records
- RELEASE.md added with verified totals and test results

## v0.10.0 - SQLite-first (2026-11-02)

### Highlights

- Migrated all lore from markdown to a single SQLite file: `db/grimoire.db`
- Added `norm_text` columns + indexes for SQL-based substring matching against all corpora
- 58,764 items, 2,699 interactions, 71 records complete
- FTS5 index over all tables
- Agents (Drifter, Eris) use `db/query.py` and `sqlite3 db/grimoire.db` for all lore lookups

### Database Tables (at release)

| Table | Rows | Purpose |
|-------|------|---------|
| books | 110 | Book metadata |
| book_entries | 1158 | Entries within books |
| transcripts | 68 | Quest transcript headers |
| transcript_lines | 1709 | Canon character dialogue |
| grimoire_cards | 2889 | Destiny 1 grimoire cards |
| interactions | 2699 | Character dialogue beats |
| items | 58764 | Weapons / armor / gear lore |
| records | 71 | Triumphs and seals |
| characters | 18 | Named characters |
| character_lines | 1054 | Character quotes |
| meta | 1 | DB version |

### Repository restructuring

- Markdown data moved to `source/` (books, cards, transcripts, records, items, interactions)
- `archive/` holds raw JSONL scraped output
- Legacy markdown indexes (`destiny-1-index.json`, `items-index.json`, `records-index.json`, `interactions/index.md`) removed
- Consolidated CHANGELOG (removed per-scrape entries)
- Reorganized test scripts: `tests/lore-integrity.sh` now 17/17 checks via SQLite

## Tests and audit

- `eris-master-audit.sh` (grimoire): 7/7 pass; (eris-morn): 8/8 pass
- `drifter-master-audit.sh`: 17/17 pass
- `tests/test-db.sh`: 29/29 pass
- `tests/lore-integrity.sh`: 17/17 pass
- `tests/drifter-quote-verify.sh`: 0 unverified (DB-backed, ~3s)
- `tests/conversation-test.sh`: PASS
- `tests/eris-conversation-test.sh`: PASS

## Contents sourced

- https://www.ishtar-collective.net (Ishtar Collective)
- YouTube cutscene compilations (captions only, no video download)
- Bungie Inc owns all Destiny property

## Summary

The lore archive is a SQLite database. Agents no longer parse markdown.
