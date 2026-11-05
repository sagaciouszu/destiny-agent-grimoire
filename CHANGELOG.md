## v0.27.4 - Agent-optimization pass: search, lookups, permissions (2026-11-05)

Investigation follow-through (`GRIMOIRE-INVESTIGATION-REPORT.md` backlog 1-12):

- Search is agent-shaped: ranked results demote stage directions (penalty 2.0)
  and unattributed cutscene captions (1.0), a new `exclude_stage` filter drops
  them entirely, and snippets grew from 10 to 25 FTS tokens so relevance is
  judgeable in one call. The row key `snip` is now `snippet`.
- One-call lookups: `find_item` rows carry flavor-text snippets and linked lore
  titles; `item()` returns a bounded dict (no `id`/`norm_text`) plus `lore`
  links. `character_info.spoken_lines` is anchored to the exact speaker with
  `is_optional=0`, matching persona.json everywhere (Eris 1,011; Ghost 2,653).
- `verify` drops the LIKE scan: index-only phrases plus an exact normalized-row
  fallback for punctuation-only canon lines. Mid-word fragments no longer
  verify (submit quotes as written).
- MCP: expanded `instructions` with a tool map and verify-before-quote policy;
  every description names every parameter; ref-format hints on
  `item`/`record`/`lore`/`seal`/`list_records` (plus a `triumphs` alias);
  resource reads cap at ~16,000 chars; the offset clamp (10,000) is documented.
- Peer permission leak closed: `sync-live-agents.sh` now denies read/glob/grep
  on peer **source repos** under Work/ as well as installed peer dirs
  (24 denies per primary agent, 48 per consult copy); deployed files regenerated.
- Grimoire skill description trimmed to 150 bytes (standard: 160) with the
  full trigger list moved into the skill body.
- Three new gates: `tests/mcp-agent-optimization-test.py` (25 checks:
  descriptions, actionable errors, snippets, clamps, resource caps, counts),
  `tests/permission-leak-audit.py` (240 checks, wired into the master audit),
  `tests/count-consistency.py` (persona vs DB vs derived prose, wired into the
  master audit). Extended suite grows to include the MCP optimization gate.
- Two aggregate transcripts (`additional-edge-of-fate-contact-drifter`,
  `youtube-destinypedia-additional`) intentionally keep an empty
  `source_url`: they compile multiple upstreams (Ishtar/Destinypedia/YouTube)
  and no single canonical URL exists; fabricating one would break provenance.

## Verification

Master audits: grimoire 13/13, Drifter 23/23, Eris 18/18, Calus 18/18,
Zavala 18/18, Ghost 18/18. Local gates: test-db 55/55, query-interface 89/89,
robustness 26/26, agent-layout 81/81, docs-audit 361 commands + skills spec,
suite-manifest 5/5, conformance, agent-connections, MCP contract 12/12,
MCP matrix 8/8 (154 calls, 3 concurrent clients, API parity),
MCP agent-optimization 25/25, permission-leak-audit 240/240,
count-consistency 17/17, retrieval ranked P@5=0.96 / MRR=1.00,
golden-voice 5/5 in all five agent repos.

## v0.27.3 - Database self-audit, meta fix and MCP CLI parity (2026-11-05)

- Database self-audit found three migration bugs, all fixed: the `meta` stamp
  reported `transcripts` as 58764 (a reused item-title counter), the build
  date was hard-coded, and a leftover DEBUG print ran on every weblore ingest.
- Normal forms are total: the 14 punctuation-only canon lines keep their
  punctuation instead of normalizing to the empty string, so `verify` matches
  them; the query-side normalizer mirrors the fallback.
- Attribution purge, verified: an empty normal form let one Destinypedia
  punctuation line's speaker (Failsafe) bleed onto 13 cutscene caption lines;
  those stay `Cutscene` now, and GAPS game dialogue counts corrected
  (D2 14,282 / D1 1,411). All other 69,204 lines byte-identical.
- `class_tag` is NULL or hunter/titan/warlock on every line (5,750 empty
  strings normalized).
- MCP reaches full CLI parity: 21 tools (`seals`, `seal`, `lore` added),
  `search` documents the `lore` type, README argument lists match the real
  signatures, and the skill and wiki list every tool and resource.
- `db/capabilities.json` documents `item_title_fts` and `meta`; a new gate
  keeps it in sync with the live schema.
- STANDARDS source hierarchy now documents the accepted `ishtar_web` tier.
- Gates grew and every citation followed: test-db 51 -> 55 (live meta stamp,
  class-tag invariant, normalization invariant, capabilities sync), mcp-test
  10 -> 12 (CLI-parity tools, stats-vs-live agreement), matrix 21 tools /
  154 calls; README, tests/README, wiki and STANDARDS counts updated.

## Verification

11/11 archive suites, 55/55 database, 89/89 query interface, 17/17 taxonomy,
11/11 source crosscheck, MCP contract 12/12, matrix 8/8 (154 calls), agent
connections 36/36, parity 60/60, onboarding 60/60, 361 documented commands,
link check 18/18. Pre/post rebuild diff: every content table byte-identical,
persona counts unchanged (Drifter 1,149, Eris 1,011, Zavala 638, Calus 456,
Ghost 2,653).
## v0.27.2 - Dialogue expansion and contract corrections (2026-11-05)

- Four partial activity transcripts expanded with **212 verified net-new
  dialogue lines** from 131 activity videos: Ketchcrash 90, PsiOps Battlegrounds
  120, Defiant Battlegrounds 120, Expedition 79 (197 -> 409 lines total).
  Junk speakers and URLs filtered; every added line spot-verified.
- Persona counts synced: Drifter 1,149, Eris 1,011, Zavala 638.
- Wiki sync: `scripts/sync-wiki.sh [--check|--push]` publishes `docs/wiki/`,
  refusing model-control tokens and content drift; the public wiki was
  republished clean (10 corrupted pages replaced).
- OpenClaw onboarding: `scripts/ensure-openclaw-mcp.sh` upserts an absolute MCP
  path into the OpenClaw config (idempotent, backs up first); wired into
  `setup.sh` and `--openclaw` sync. Doctor lint: `ok: true, findings: []`.
- STANDARDS corrections: tier-aware provenance URLs, complete gate list,
  release/metadata rules aligned with conformance, approval nuance.

## v0.27.1 - Portability, safety and speaker identity (2026-11-05)

- Saint-14 speaker family protected: `Saint-XIV`, `Saint XIV`, `Saint IV`,
  `The Saint`, `Saint`, `Kellbreaker` all alias to `Saint-14`, and migration
  never drops an aliased or `Saint-*` speaker. Regression test added.
- Windows: hash-locked dependencies (`requirements.windows.lock.txt`, includes
  pywin32), `run.ps1` launcher, `windows-latest` CI job exercising build,
  probes, MCP contract, tree mirror and an agent junction setup.
- Agent sync converges to zero drift: explicit entry delivery, transformed-file
  mtime alignment; stray `.git` directories removed from deployed workspaces.
- Personal-path guards now detect any `/home/<user>` pattern instead of one
  username; machine paths scrubbed from template docs.
- Every tag in every repository now has a GitHub release (19 backfilled).
- Docs: verify examples use real canon quotes; Agent Skills frontmatter and
  `.cmd`/`.ps1` launcher targets are audited; `latest` release pinned for the
  0.x line despite historical 1.x tags.

- Wiki sync: `scripts/sync-wiki.sh [--check|--push]` publishes `docs/wiki/` to
  the GitHub wiki and refuses model-control tokens or content drift.
- OpenClaw onboarding: `scripts/ensure-openclaw-mcp.sh` upserts an absolute
  MCP path into `openclaw.json` (idempotent, backs up first); wired into
  `setup.sh` and `--openclaw` sync. Doctor lint: `ok: true, findings: []`.

## v0.27.0 - Windows portability, suite manifests and wiki (2026-11-05)

- Season 27 and Season 28 transcripts added (27 and 202 lines); all 28 seasons
  now have at least one transcript. Crota's End and Wrath of the Machine are
  confirmed `no_dialogue`.
- Per-agent `suites.json` manifests plus a shared runner; central no-loss guard
  (`tests/suite-manifest-test.py`) keeps every master-audit suite intact.
- Versioned wiki added under `docs/wiki/` with copyedited setup, architecture,
  CLI, MCP, agent, platform, testing and troubleshooting pages.
- Windows portability: `mcp-server/run.cmd`, venv-layout detection in
  `run.sh`/`install.sh`, rsync-free tree mirror for agent sync, and a
  symlink -> junction -> clone fallback in every `setup.sh`.
- MCP probe (`mcp-server/probe.sh`) performs a real handshake and reports the
  18 tools; OpenClaw absolute-path guidance documented.
- Documentation audits fixed: suite counts, season counts, command targets,
  stale view counts; MCP coverage results expose `coverage_status` and
  `coverage_notes`.
- External link check no longer runs on a schedule; it runs after deploys, on
  pull requests and on manual dispatch.

## v0.26.0 - Reviewed activity dialogue and coverage status (2026-11-04)

- Reviewed dialogue for Ketchcrash (38), PsiOps Battlegrounds (51), Defiant
  Battlegrounds (73) and Expedition (35), marked `partial_transcript`.
- `coverage_notes` statuses: `no_dialogue`, `narration_only`,
  `dialogue_source_missing`, `partial_transcript`, `unverified`.
- Crow identity canonicalized to `Crow`; regression test added.
- API, CLI, MCP and activity detail return coverage statuses; onboarding 60/60.

## v0.25.0 - Activity transcript coverage (2026-11-04)

- Ten Destinypedia transcripts plus four Destiny 1 raid encounter transcripts.
- Activities with no transcript: 19 -> 4; dungeons and exotic missions covered.
- Gap ledger reports activities, seasons, events and sparse speakers by status.

## v0.24.0 - Authoritative releases and Destiny 1 coverage (2026-11-04)

- Authoritative Ishtar `Added In` release for 1,130 transcripts.
- Transcript explicit classification 104 -> 1,234; Destiny 1 0 -> 120.
- Scraped footers and related-content rows removed from canon.

## v0.23.0 - Class-tagged canon and user preferences (2026-11-04)

- `transcript_lines.class_tag` tags Hunter, Titan and Warlock variants.
- Menagerie class callouts are optional, preserving 419 base Calus lines and 12 variants.
- `--class hunter|titan|warlock` on `search`, `character` and `transcript`.
- Agent `memory.py` gains per-user `prefs-get` / `prefs-set --class`.
- `USER.template.md` and agent guidance store the class once and use it for canon.
- Schema 1.3.0; query interface 89 checks.

## v0.22.0 - Manifest lore, Commons transcripts and source tiers (2026-11-04)

- 2,962 Bungie manifest lore entries (1,962 new after dedupe) with item links.
- Full manifest activity catalogue: 3,744 activities, seasons 27-28, 314 links.
- Crawled 862 Ishtar Commons topics; 37 net-new transcripts after dedupe.
- `source_tier` records Ishtar > Destinypedia > captions precedence.
- `section` and `is_optional` preserve locations, alternatives and class callouts.
- `--canon-only`, `--section`, `list lore`, `lore` command and `--type lore`.
- Seal tree: 70 seals and 1,004 triumph records (`seal`, `seals`, `list seals`).
- Schema 1.2.0; manifest version pinned in `meta`.

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
- Verbatim activity transcripts from Destinypedia: Menagerie (232 Calus lines,
  class callouts kept separate), raids, dungeons, exotic missions and seasonal
  activities. Calus 431 lines, Rhulk 36, Nezarec 28.
- Quest-step titles parsed as speakers are filtered out (504 noise rows).
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
