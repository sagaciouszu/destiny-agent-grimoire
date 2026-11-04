# Discovery Design

## The problem

The grimoire had one discovery primitive: FTS5 over every text row, filtered by
`source` (`transcript_line`, `book_entry`, `item`, ...). That answers "where is
this word" but not:

- all raid dialogue
- every Calus line from the Menagerie
- Festival of the Lost content across years
- what a season actually contains
- what is vaulted

`transcripts.release` and `transcripts.arc` were free text and mostly empty:
1,130 of 1,229 rows had no release and 1,170 no arc when this work started.
Items and records carried their own inconsistent release strings. Nothing
joined them.

## The model

Four independent axes, additive to the canon tables:

| Axis | Table | Cardinality |
|---|---|---|
| Expansion | `expansions` | 18 |
| Season / episode | `seasons` | 26 (official numbers) |
| Activity | `activities` | 67 |
| Event | `events` + `event_occurrences` | 9 events, 72 occurrences |

Classification lives in `transcript_classification`, `item_classification` and
`document_classification`, each with `confidence` and `evidence`.

## Why additive

- Existing tables, columns, views, queries, CLI commands and MCP tools keep
  working unchanged.
- `release` and `arc` stay as fallback text; they are not migrated or deleted.
- A failed classification leaves `unknown`, never a guess.
- The taxonomy can be rebuilt independently with `python3 db/taxonomy.py`.

## Why not one `season_id` column

A transcript can be a raid from one expansion, an activity from a season, and
part of a recurring event. Collapsing that into one column forces a lossy
choice. Events repeat, so they need occurrences, not a season foreign key.
Episodes are not ordinary seasons, so they carry `season_type='episode'` and an
`act` rather than pretending to be seasons 24-26 in the old sense.

## Confidence

| Value | Source |
|---|---|
| `explicit` | `release` or `arc` named the axis |
| `derived` | activity catalogue, title, story arc or date range matched |
| `manual` | curated override |
| `unknown` | nothing matched |

Current transcript split: 104 explicit, 801 derived, 389 unknown (30%). The
unknown set is mostly story beats whose titles carry no release metadata. They
remain searchable by text; they are simply not attributed.

## Query behaviour

Filters compile to `fts.source_slug IN (subquery)` so FTS still drives the scan
and the taxonomy tables answer the membership question.

Measured on 122,259 FTS rows, 10 results:

| Query | Time |
|---|---|
| unfiltered `calus` | 18 ms |
| `--season 7` | 7 ms |
| `--activity menagerie` | 4 ms |
| `--event the-dawning` | 5 ms |
| `--expansion the-final-shape` | 14 ms |

No new full scans were introduced; the activity filter uses
`idx_tc_activity`.

## What agents get

- CLI: `--activity`, `--season`, `--event`, `--expansion`; `activity`, `event`,
  `coverage`.
- MCP: the same filters on `search`; `activities`, `activity`, `seasons`,
  `events`, `event`, `coverage` tools.
- API: `api.activities()`, `api.activity()`, `api.seasons()`, `api.events()`,
  `api.event()`, `api.coverage()`, plus filter kwargs on `search` and
  `search_total`.
- Views: `v_transcript_taxonomy`, `v_activity_coverage`,
  `v_season_coverage`, `v_event_coverage`.

## Lore and seals

Manifest lore entries, seals and triumphs are additive enrichment, not canon
dialogue. They are indexed for discovery (`source=lore_entry`), while seal and
triumph descriptions stay out of `verify_fts`. `lore`, `seal` and `seals`
provide direct lookups.

## Source tiers

`transcripts.source_tier` records precedence: Ishtar main and tagged Commons
above untagged Commons, above Destinypedia, above captions. Optional lines are
flagged with `is_optional`; `--canon-only` excludes them.

## Limits

- Source scarcity, not schema, is the remaining constraint. Several vaulted
  raids have no surviving transcript source.
- Item classification relies on release strings and title keywords; 12,070
  items remain `unknown`.
- Authoritative Bungie manifest ingestion needs an API key. The curated
  catalogue is the fallback and is documented as such.

See `docs/TAXONOMY.md` for the contract and `db/taxonomy.py` for the catalogue.
