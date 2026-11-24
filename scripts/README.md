# Scripts

Active ingestion utilities for curated content types. Bulk extraction tooling
(scrapers, caption fetchers) is vault-local and not committed.
Output feeds `db/migrate.py`; re-run migrate after ingesting.

| Script | Writes to | Consumed by migrate |
|--------|-----------|---------------------|
| `build-lore-staging.py` | `archive/data/manifest/lore_entries.jsonl` | no (enrichment input) |
| `gap-report.py` | stdout | no (generated report) |
| `ingest-ishtar-commons-batch.py` | `source/transcripts/commons-*.md` | yes |
| `ishtar-timeline.py --fetch/--from/--report` | `source/ishtar-timeline.json` | yes (in-universe era snapshot; --report compares vs the timeline column) |

The retained batch importer is resumable/idempotent and formats output as
`# Title` + `- Source:` + body, matching the migrate parsers. A retired
Destinypedia one-off kept every "or alternatively" and class-exclusive
variant; it never merged them.

## Operations

| Script | Purpose |
|--------|---------|
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

Bulk content (items, interactions, web transcripts, cutscene captions) is
ingested with vault-local scrapers writing JSONL; those inputs are local-only
and not committed.

## Retired scripts (removed from git 2026-11-16)

The one-off extraction utilities (Destinypedia/Ishtar/commons ingest, record
ingest, VO-caption attribution, containment evidence ledger) were removed
from git with the extraction corpora; the operator vault retains a copy.
Current corpus data remains in `source/`, and verification logic remains
covered by `tests/containment-test.py`.

Other scripts in this directory remain active: in particular, the live-build
orchestration steps, `generate-knowledge-web.py` (master-audit gate),
`sync-wiki.sh`, and the locale/language validation tools are intentionally
retained.
