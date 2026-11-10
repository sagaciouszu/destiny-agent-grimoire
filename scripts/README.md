# Scripts

One-off ingestion utilities for content types not covered by `archive/scrape.py`.
Output feeds `db/migrate.py`; re-run migrate after ingesting.

| Script | Writes to | Consumed by migrate |
|--------|-----------|---------------------|
| `build-lore-staging.py` | `archive/data/manifest/lore_entries.jsonl` | no (enrichment input) |
| `crawl-ishtar-commons.py` | `archive/data/commons/` (local) | no (raw crawl) |
| `gap-report.py` | `docs/GAPS.md` | no (generated report) |
| `ingest-destinypedia.py --page ... --slug ...` | `source/transcripts/` | yes (globs `source/transcripts/*.md`) |
| `ingest-grimoire.py <slug>...` | `source/cards/` | yes (globs `source/cards/*.md`) |
| `ingest-ishtar-commons-batch.py` | `source/transcripts/commons-*.md` | yes |
| `ingest-ishtar-commons.py --topic N --slug ...` | `source/transcripts/` | yes (globs `source/transcripts/*.md`) |
| `ingest-record.py <slug>...` | `source/records/` | yes (globs `source/records/*.md`) |
| `ishtar-timeline.py --fetch/--from/--report` | `source/ishtar-timeline.json` | yes (in-universe era snapshot; --report compares vs the timeline column) |

All are resumable/idempotent and format output as `# Title` + `- Source:` +
body, matching the migrate parsers. `ingest-destinypedia.py` keeps every
"or alternatively" and class-exclusive variant; it never merges them.

## Operations

| Script | Purpose |
|--------|---------|
| `../archive/data/fetch_transcript_releases.py` | authoritative transcript release map |
| `../db/build-slim.py [out]` | 224 MB core database: books, transcripts, captions, interactions, records (no items/cards) |
| `../db/enrich_itemsets.py --apply` | curated armour-set classification |
| `../db/enrich_lore.py` | manifest lore entries and FTS/verify |
| `../db/enrich_manifest.py` | manifest activities, seasons and links |
| `../db/enrich_seals.py` | seal/triumph tree |
| `backup.sh [zip]` | rolling archive backup without the database, plus checksum |
| `coverage-report.py` | Markdown coverage report from the live database |
| `refresh-live-build.py --source DIR [--dry-run]` | unpack/merge/resolve/extract/validate/combine a new live build, register it, rebuild and gate |
| `export-site-stats.py --out PATH` | one JSON snapshot of counts/sizes for the site |
| `generate-knowledge-web.py --check\|--apply` | managed canon snapshot in each agent `reference/knowledge-web.md` |
| `ensure-openclaw-mcp.sh` | keep OpenClaw's MCP pointer at the stable grimoire wrapper (idempotent, backs up first, skips when OpenClaw is absent) |
| `release-stage.sh <version> [--dry-run]` | copy the database, write `SHA256SUMS`, print publish commands |
| `sync-live-agents.sh [--openclaw] [--dry-run]` | deploy every agent in `series/agents.json` into OpenCode (agents/) or OpenClaw (workspace-<id>), preserving runtime memory and series blocks; skips agents with persona.json ready=false |
| `sync-wiki.sh [--check\|--push]` | sync `docs/wiki/` into the GitHub wiki clone; `--check` fails on drift or model-control tokens, `--push` publishes |

Bulk content (items, interactions, web transcripts, cutscene captions) uses
the scrapers in `archive/` writing JSONL:

- `archive/scrape.py` - items, interactions
- `archive/data/fetch_transcripts_web.py` - all Ishtar transcript pages
- `archive/data/fetch_cutscenes.py` - cutscene compilation captions
