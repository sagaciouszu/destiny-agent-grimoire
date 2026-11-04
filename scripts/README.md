# Scripts

One-off ingestion utilities for content types not covered by `archive/scrape.py`.
Output feeds `db/migrate.py`; re-run migrate after ingesting.

| Script | Writes to | Consumed by migrate |
|--------|-----------|---------------------|
| `ingest-grimoire.py <slug>...` | `source/cards/` | yes (globs `source/cards/*.md`) |
| `ingest-record.py <slug>...` | `source/records/` | yes (globs `source/records/*.md`) |
| `ingest-destinypedia.py --page ... --slug ...` | `source/transcripts/` | yes (globs `source/transcripts/*.md`) |
| `ingest-ishtar-commons.py --topic N --slug ...` | `source/transcripts/` | yes (globs `source/transcripts/*.md`) |

All are resumable/idempotent and format output as `# Title` + `- Source:` +
body, matching the migrate parsers. `ingest-destinypedia.py` keeps every
"or alternatively" and class-exclusive variant; it never merges them.

## Operations

| Script | Purpose |
|--------|---------|
| `release-stage.sh <version> [--dry-run]` | copy the database, write `SHA256SUMS`, print publish commands |
| `backup.sh [zip]` | rolling archive backup without the database, plus checksum |
| `sync-live-agents.sh [--openclaw] [--dry-run]` | deploy every agent in `series/agents.json` into OpenCode (agents/) or OpenClaw (workspace-<id>), preserving runtime memory and series blocks; skips agents with persona.json ready=false |
| `../db/build-slim.py [out]` | 95 MB core database: books, transcripts, interactions, records (no items/cards) |
| `coverage-report.py` | Markdown coverage report from the live database |

Bulk content (items, interactions, web transcripts, cutscene captions) uses
the scrapers in `archive/` writing JSONL:

- `archive/scrape.py` - items, interactions
- `archive/data/fetch_transcripts_web.py` - all Ishtar transcript pages
- `archive/data/fetch_cutscenes.py` - cutscene compilation captions
