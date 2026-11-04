# v0.21.0 - Activity, season and event taxonomy

**2026-11-04**

## What's Changed

- **Four-axis taxonomy:** expansion, official numeric season/episode, activity
  and rotating event, stored additively alongside canon tables.
- **Catalogue:** 18 expansions, 26 seasons/episodes, 67 activities, 9 events and
  72 event-year occurrences, including vaulted content.
- **Classification:** 1,249 transcripts, 58,764 items and 181 books/records
  tagged with confidence (`explicit`, `derived`, `manual`, `unknown`) and evidence.
- **Discovery:** activity/season/event/expansion filters on search; `activity`,
  `event` and `coverage` commands; `activities`, `activity`, `seasons`, `events`,
  `event` and `coverage` MCP tools.
- **Content:** verbatim Destinypedia transcripts for the Menagerie (232 Calus
  lines, class callouts kept separate), raids, dungeons, exotic missions and
  seasonal activities. Calus 431 lines, Rhulk 36, Nezarec 28.
- **Quality:** quest-step titles parsed as speakers are filtered out; `unknown`
  transcript classification fell from 54% to 31%.
- **Docs:** `docs/TAXONOMY.md`, `docs/DISCOVERY.md`, schema contract in
  `STANDARDS.md`, updated CLI, MCP and README surfaces.

## Verification

9/9 archive, 76/76 interface, 14/14 layout, 8/8 MCP, 141-call matrix, 8/8 extended, conformance PASS. Drifter 20/20 and Eris 15/15 in their repos.

## Asset

`grimoire.db` with verification, item-title and taxonomy indexes. `SHA256SUMS` is attached.
