# Destiny Agent Grimoire

<p align="center">
  <img src='header.png' alt='Destiny Agent Grimoire' width='100%'/>
</p>

<p align="center">
  <img src='https://img.shields.io/github/v/tag/sagaciouszu/destiny-agent-grimoire?label=version&color=blue' alt='Version'/>
  <img src='https://img.shields.io/github/last-commit/sagaciouszu/destiny-agent-grimoire?label=last%20push&color=blue' alt='Last push'/>
  <img src='https://img.shields.io/badge/license-MIT-green' alt='License'/>
  <img src='https://img.shields.io/badge/tests-11%2F11%20passing-brightgreen' alt='Tests'/>
</p>

**Version:** 1.9.0 | **Last push:** 2026-11-03 | **Status:** Active

One canonical, agent-first Destiny lore archive: a single SQLite database with
FTS5 search, built from committed sources, with a documented quote policy and
verification gates. No external services at runtime.

## Quick start for Guardians

**Step 1: clone.**

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
```

**Step 2: get the database. Run exactly one of these, not both.**

Download the prebuilt release asset (seconds):

```bash
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
```

The agent installers verify the download against the release `SHA256SUMS`.

Or build from this checkout (about two minutes, matches this commit):

```bash
python3 db/migrate.py
```

**Step 3: query.**

```bash
python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
```

**Optional: MCP clients.** Install the typed tool adapter once:

```bash
bash mcp-server/install.sh
```

It prints a client config snippet pointing at `mcp-server/run.sh`. Details and
the tool list: `mcp-server/README.md`.

More commands are in the sections below.

## Requirements

| Requirement | Needed for | Notes |
|---|---|---|
| `python3` 3.8+ | migration, query CLI, tests | standard library only |
| `sqlite3` | optional raw SQL | the CLI uses Python's built-in driver |
| `curl` | optional prebuilt database | otherwise build locally |
| MCP SDK (optional) | typed tools for agents without a shell | Python 3.10+; `bash mcp-server/install.sh` |
| `git` | cloning and version history | |
| ~260 MB disk | sources plus built database | database is ~170 MB |

No API keys, accounts or network access are required at runtime.

## What is inside

| Table | Rows | Purpose |
|---|---|---|
| `books` | 110 | Book-level metadata |
| `book_entries` | 1158 | Lore entries within books |
| `transcripts` | 1229 | Transcript headers |
| `transcript_lines` | 71221 | Canon dialogue (speaker, line) |
| `grimoire_cards` | 2889 | Destiny 1 grimoire cards |
| `interactions` | 2699 | Short dialogue beats |
| `items` | 58764 | Weapons, armor and gear lore |
| `records` | 71 | Triumphs and seals |
| `characters` | 20 | Curated character index |
| `character_lines` | 1229 | Quote-ready character lines |
| `fts` | 120731 | FTS5 index over all content |
| `v_speakers` (view) | 359 | Canonical speakers with line counts |
| `speaker_aliases` | 6 | Alias to canonical speaker mapping |
| `verify_fts` (index) | 120731 | Fast quote verification |
| `item_title_fts` (index) | 58764 | Item title lookup |

Every content row carries provenance. Speaker aliases are canonicalized during
migration. The full contract is `STANDARDS.md`.

## For agents

- **Skill:** `skills/destiny-grimoire/SKILL.md` is the drop-in agent skill.
- **MCP (optional):** `mcp-server/run.sh` serves typed tools to non-shell clients
  over local stdio; one adapter covers every agent that mounts this archive.
  Install with `bash mcp-server/install.sh`; tools, limits, client config and
  security: `mcp-server/README.md`.
- **Interface:** one of `python3 db/query.py search|character|item|verify|book|transcript|find-item|record|list|stats`; read commands accept `--offset`.
  `verify` is the quote-safety primitive (exit 1 when absent); every command
  accepts `--json`; search returns snippets unless `--full`.
- **Discovery:** `db/capabilities.json` is a machine-readable manifest of tables,
  views, commands and contracts.
- **Search surface:** FTS5 with a `source` column for exact type filters.
- **Policy:** `STANDARDS.md` defines schema, naming, provenance, quote policy and
  verification gates.
- **Never** parse `source/` markdown at runtime. Query the database.
- **Output budget:** always pass `--limit`; assume 20 to 40 lines per call.

Connection matrix:

| From | To | Mechanism |
|---|---|---|
| agent repos | this archive | `lore/` symlink or clone, then `lore/db/query.py` |
| agent `setup.sh` | this archive | clone or symlink, download or build the database |
| MCP client | this archive | `mcp-server/run.sh` (stdio, read-only) |
| release workflow | consumers | `grimoire.db` attached to each release, checksum verified |

## Repository layout

```
db/          # query.py, schema.sql, migrate.py, capabilities.json (grimoire.db is built)
source/      # ingested markdown: books, cards, transcripts, records, items, interactions
compendium/  # character quote index that feeds the characters tables
archive/     # raw scraper output (JSONL) and fetchers
scripts/     # ingestion helpers
tests/       # archive gates, agent suites, shared runner, conformance
skills/      # agent-facing SKILL.md
mcp-server/  # optional MCP adapter (stdio, read-only)
index.md     # short pointer to the database
STANDARDS.md # the contract: schema, naming, provenance, gates, README rules
```

## Maintenance

```bash
# ingest more content (Ishtar page ranges, caption fetchers)
python3 archive/scrape.py interactions <start> <end>
python3 archive/scrape.py items <start> <end>
python3 archive/data/fetch_transcripts_web.py
python3 archive/data/fetch_cutscenes.py

# rebuild and sync documented counts
python3 db/migrate.py
python3 tests/sync-doc-counts.py
python3 tests/sync-readme-meta.py

# verify everything
bash grimoire-master-audit.sh
bash drifter-master-audit.sh
bash eris-master-audit.sh

# stage a release (copy, checksums, publish commands), backup, sync agents
bash scripts/release-stage.sh <version>
bash scripts/backup.sh
bash scripts/sync-live-agents.sh

# release the database as an asset (digest checked against local sha256)
gh release upload <tag> db/grimoire.db SHA256SUMS --clobber
```

The change procedure is section 10 of `STANDARDS.md`. A rolling backup of the
repository minus the database lives outside the tree.

## Verification

| Suite | Command | Expected |
|---|---|---|
| Archive audit | `bash grimoire-master-audit.sh` | 11/11 |
| Drifter agent audit | `bash drifter-master-audit.sh` | 18/18 |
| Eris agent audit | `bash eris-master-audit.sh` | 13/13 |
| Database integrity | `bash tests/test-db.sh` | 38 checks |
| Query interface | `bash tests/query-interface-test.sh` | 29 checks |
| Cutscene captions | `bash tests/cutscene-verify.sh` | 6/6 checks |
| MCP contract | `mcp-server/.venv/bin/python tests/mcp-test.py` | 6/6 checks |
| File conformance | `python3 tests/conformance.py` | PASS |

Agent audits need their workspaces present; the archive audit skips
workspace-only suites when they are absent.

## License and attribution

MIT licensed. Fan-made. Not affiliated with or endorsed by Bungie.

### Licensing

- Original code, tests and documentation are MIT licensed; see `LICENSE`.
- Destiny lore, text, characters and art belong to Bungie. No license is granted
  to Bungie IP.
- This is a fan-made, non-commercial project; `NOTICE` records the split.

- **Destiny 1 and Destiny 2** content and related intellectual property belong to Bungie.
- **Ishtar Collective** (https://www.ishtar-collective.net): the primary text
  archive; their transcription work is the foundation this project rests on.
- **Destiny Lore Vault** (https://www.youtube.com/@DestinyLoreVault): the recording
  archive; their videos keep the performances behind the words alive.
- **Destinypedia** (https://www.destinypedia.com): bootstrap source for specific dialogue.
- **Destiny community**: transcription, analysis and preservation, with
  **special thanks to every Guardian making their own fate in 2026 and beyond**.

All the community projects out there are continual labors of love. Neither this
archive nor the community around it would exist without the efforts of everyone
who has worked on Destiny.

Cutscene transcripts come from YouTube captions (auto-generated, corroboration
verified). Content and provenance are documented in `STANDARDS.md`.
