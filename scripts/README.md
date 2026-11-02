# Scripts

One-off ingestion utilities for content types not covered by `archive/scrape.py`.
Output feeds `db/migrate.py`; re-run migrate after ingesting.

| Script | Writes to | Consumed by migrate |
|--------|-----------|---------------------|
| `ingest-grimoire.py <slug>...` | `source/cards/` | yes (globs `source/cards/*.md`) |
| `ingest-record.py <slug>...` | `source/records/` | yes (globs `source/records/*.md`) |

Both are resumable (existing slugs are skipped) and format output as
`# Title` + `- Source:` + body, matching the migrate parsers.

Bulk content (items, interactions, web transcripts, cutscene captions) uses
the scrapers in `archive/` writing JSONL:

- `archive/scrape.py` - items, interactions
- `archive/data/fetch_transcripts_web.py` - all Ishtar transcript pages
- `archive/data/fetch_cutscenes.py` - cutscene compilation captions
