# Activity, Season, Event and Expansion Taxonomy

The grimoire classifies content on four independent axes. They are additive:
canon tables (`transcripts`, `transcript_lines`, `books`, `items`, `records`)
are never rewritten by the taxonomy, and every existing query still works.

| Axis | Table | Example |
|---|---|---|
| Expansion | `expansions` | `forsaken`, `the-final-shape`, `renegades` |
| Season / Episode | `seasons` | season 17 = `season-of-the-haunted`; season 24 = `episode-echoes`; season 27 = `season-reclamation` |
| Activity | `activities` | `last-wish` (raid), `duality` (dungeon), `menagerie` (seasonal) |
| Event | `events` + `event_occurrences` | `festival-of-the-lost`, `the-dawning`, `crimson-days` |

## Season numbering

`seasons.season_number` is Bungie's official numeric slot, not a local counter.

- Seasons 1–23 are ordinary seasons (`season_type = 'season'`).
- Seasons 24–26 are episodes (`season_type = 'episode'`) and also carry an
  `act` on classified content when the title names Act I, II or III.
- Seasons 27 (`Season: Reclamation`) and 28 (`Monument of Triumph`) come from
  the official manifest, aligned to The Edge of Fate and Renegades.

Aliases resolve to one record:

```text
17, "Season 17", "Season of the Haunted", "haunted"
  -> season-of-the-haunted
```

## Classification and confidence

`transcript_classification` has one row per transcript. `item_classification`
and `document_classification` cover items, books and records.

`confidence` is one of:

| Value | Meaning |
|---|---|
| `explicit` | the source's `release`/`arc` metadata named the axis |
| `derived` | the activity catalogue, title, story arc or date range matched |
| `manual` | a curated override was applied |
| `unknown` | nothing matched; the row is left unclassified rather than guessed |

`evidence` records what matched, for example
`activity:nightmare containment,activity_catalog`.

Current state (2026-11-04):

| Content | explicit | derived | unknown |
|---|---:|---:|---:|
| Transcripts (1,308) | 1,248 | 59 | 1 |
| Items (58,764) | 48,380 | 871 | 9,513 |
| Books + records (181) | 64 | 4 | 113 |

Every Ishtar web transcript now carries the page's authoritative `Added In`
release (1,130/1,130), captured by
`archive/data/fetch_transcript_releases.py`. That is why transcript coverage is
near-complete and why Destiny 1 content is now visible: 123 transcripts and
1,412 dialogue lines across `destiny-1`, `the-dark-below`, `house-of-wolves`,
`the-taken-king` and `rise-of-iron`.

Ten Destinypedia verbatim transcripts close the remaining activity gaps where
that wiki has a `Transcript` section: Salvation's Edge, Spire of Stars, Eater of
Worlds, The Shattered Realm, Seraph's Shield, Starcrossed, Enigma Protocol,
Kell's Fall, Deep Dives and Altars of Summoning. Four Destiny 1 raid encounter
transcripts are narration-only and are labelled that way in `docs/GAPS.md`.
A Destiny 1 expansion never inherits a Destiny 2 season from a reprised
activity, so Vault of Glass and King's Fall stay seasonless.

Manifest item sets provide an optional classification gain: 19 curated sets
resolve 555 items that are still `unknown` (10,068 -> 9,513). The mapping lives
in `db/enrich_itemsets.py` and only fills rows that are still unclassified.

The one remaining unknown transcript is a beta entry with no release page. It
remains fully searchable by text; it is simply not attributable to a season or
activity yet.

The Menagerie is ingested from Destinypedia's verbatim transcript: 232 Calus
lines across every encounter, including the Hunter, Titan and Warlock callouts.
All class variants are separate rows; none are deduplicated.

## Vaulted content

`vaulted = 1` marks content removed from the live game but retained in the
archive: early seasons, Crimson Days, The Revelry, old raids and destinations.
Vaulted content is never hidden from search.

## Discovery

CLI:

```bash
python3 db/query.py coverage                       # full coverage matrix + gaps
python3 db/query.py list activities --limit 20
python3 db/query.py list seasons
python3 db/query.py list events
python3 db/query.py activity menagerie
python3 db/query.py event festival-of-the-lost
python3 db/query.py search calus --season 7 --limit 5
python3 db/query.py search shaxx --event "Iron Banner"
python3 db/query.py search crota --activity "crown of sorrow"
python3 db/query.py search witness --expansion "The Final Shape"
```

MCP tools: `activities`, `activity`, `seasons`, `events`, `event`, `coverage`,
plus `activity` / `season` / `event` / `expansion` filters on `search`.

Python API: `api.activities()`, `api.activity(ref)`, `api.seasons()`,
`api.events()`, `api.event(ref)`, `api.coverage()`, and the same filters on
`api.search()` and `api.search_total()`.

## Views

| View | Purpose |
|---|---|
| `v_transcript_taxonomy` | transcript header joined to its classification |
| `v_activity_coverage` | transcripts and spoken lines per activity |
| `v_season_coverage` | transcripts and spoken lines per season |
| `v_event_coverage` | transcripts, lines and occurrence count per event |

## Rules for maintainers

1. Add catalogue rows in `db/taxonomy.py`, never by hand in SQL.
2. Keep season numbers official; do not renumber.
3. Events repeat across seasons, so they use `event_occurrences`, not a season id.
4. Never guess a classification to reduce the `unknown` count.
5. `python3 db/taxonomy.py` re-runs classification on an existing database;
   `python3 db/migrate.py` rebuilds everything from source.
