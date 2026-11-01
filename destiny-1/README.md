# Destiny 1 - Grimoire (In Progress)

Destiny 1 (2014) grimoire cards ingested from the Ishtar Collective.
Status: in-progress (sample batch ingested; full ingestion pending).

## Status
- Source: https://www.ishtar-collective.net (Grimoire Cards document type)
- Scope: ~4000+ grimoire cards across categories (Alliances, Enemies, Places, etc.)
- Ingested so far: 10 cards (sample batch from page 1)
- Index: destiny-1/index.md
- Cards: destiny-1/cards/<slug>.md

## Ingestion method
Use `scripts/ingest-grimoire.py <slug1> <slug2> ...` (see /tmp or repo scripts).
Entries are fetched from https://www.ishtar-collective.net/entries/<slug>.
Body extracted from `<div class="description highlightable">`.

## Enumerating remaining cards
Browse https://www.ishtar-collective.net/entries/page/N?document_type_id=2
(145 pages, ~30 cards per page). Full enumeration is a multi-session effort.

## Note
Until fully ingested, agents should treat Destiny 1 lore as partial. Do not fabricate.
