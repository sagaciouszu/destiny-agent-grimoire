# Interactions - Character Dialogue Index

Agent-optimized index of Destiny character interactions (single-line and multi-line dialogue).
Source: https://www.ishtar-collective.net/interactions

## Agent Query
- `interactions/index.json` - machine-readable index (slug, title, speaker, quote, release).
- Lookup by speaker: filter entries where `speaker` matches.
- Lookup by keyword: grep the quote field or use python.

## Status
- Ingested: 1000 | Total: ~3100+ interactions across ~100 pages
- Enumeration: https://www.ishtar-collective.net/interactions/page/N

## Ingestion
Use `scripts/ingest-interaction.py <slug1> <slug2> ...`.
