# Items - Gear Lore (Pending)

Destiny item lore (weapons, armor, ghosts, ships, etc.) from Ishtar Collective.
Status: in-progress. Ingested: 481. Source: https://www.ishtar-collective.net/items (~3200+ items across ~100 pages).

## Enumeration
https://www.ishtar-collective.net/items/page/N

## Ingestion plan
Fetch each item entry, extract body from `<div class="description highlightable">`, store in `items/<slug>.md`.
