# Destiny 1 - Grimoire (In Progress)

Destiny 1 (2014) grimoire cards ingested from the Ishtar Collective.
Status: in-progress (~2889 of ~4000+ cards ingested, pages 1-145).

## Agent Query Guide
- `destiny-1/index.json` - machine-readable slug→title map (O(1) lookup).
- `destiny-1/index.md` - human/agent table (slug | title | status).
- `destiny-1/cards/<slug>.md` - individual card text.
- To find a card by keyword: `grep -rli "keyword" destiny-1/cards/`.
- To find a card by title: look up slug in index.json or index.md.

## Status
- Source: https://www.ishtar-collective.net (Grimoire Cards document type)
- Scope: ~4000+ grimoire cards across categories
- Ingested: 2889 cards (pages 1-145 of 145)
- Index: destiny-1/index.md, destiny-1/index.json
- Cards: destiny-1/cards/<slug>.md

## Ingestion method
Use `scripts/ingest-grimoire.py <slug1> <slug2> ...`.
Entries fetched from https://www.ishtar-collective.net/entries/<slug>.
Body extracted from `<div class="description highlightable">`.
Enumerate remaining: https://www.ishtar-collective.net/entries/page/N?document_type_id=2

## Note
Until fully ingested, agents should treat Destiny 1 lore as partial. Do not fabricate.
