# Tests

This directory contains validation scripts for the archive.

## Categories

### Archive-agnostic (test the data, not any agent persona)
- `test-db.sh` - database integrity (29 checks: tables, FTS, orphans, counts)
- `validate.sh` - consistency check (quotes, links, index)
- `lore-integrity.sh` - archive structure (books, transcripts, index, slug/file mapping)
- `lore-quote-count.sh` - per-character transcript line counts vs database
- `lore-format.sh` - source markdown transcript format (68/68)
- `compendium-check.sh` - compendium files present and non-empty
- `query-interface-test.sh` - the agent-facing query.py contract (23 checks)
- `cutscene-verify.sh` - cutscene captions vs canonical transcripts (8-gram shingles: corroboration, encoding, attribution)
- `conversation-test.sh` / `eris-conversation-test.sh` - agent queries hit SQLite
- `ci-checks.py` - stale refs, em-dashes (agent files), personal paths, headers, circular/self deps
- `sync-doc-counts.py` - rewrite doc count claims from the database (`--check` for CI-style staleness gate)
- `conformance.py` - per-file conformance across all three repos (headers, refs, token-estimate accuracy, persona-agnostic grimoire)
- `source-overlap-verify.py` - curated markdown vs live Ishtar overlap + filename/source-slug integrity
- `speaker-audit.py` - parse-noise regression gate for speaker names
- `live-sample-verify.py` - on-demand live coverage probe per content type (network)

### Utilities
- `yt-transcript.sh` / `yt-batch.sh` - YouTube caption extraction (subtitle-only, no video) to `source/transcripts/`

### Agent-integration (test a specific agent persona against this archive)
- `drifter-*` scripts - validate the Drifter agent's voice, modules, scenarios, etc.
- `drifter-quote-verify.sh` - all quoted strings in Drifter files trace to the DB (DB-backed, ~3s)
- `drifter-master-audit.sh` (at repo root) - unified Drifter audit (17 suites)
- `eris-master-audit.sh` (at repo root) - unified Eris audit (6 suites)

These integration tests are kept here for backward compatibility with consumers
(e.g., how-to-drift-for-agents). They are not required for archive integrity.

## Scrapers (archive/data/)
- `archive/data/fetch_transcripts_web.py` - all Ishtar transcript pages -> `transcripts_web.jsonl`
- `archive/data/fetch_cutscenes.py` - cutscene compilation captions (subtitle-only, no video) -> `cutscenes.jsonl`

Both feed `db/migrate.py`; re-run migrate after fetching.
