# Query CLI

`db/query.py` is the shell interface to the archive. It uses the standard
library and opens the database read-only.

## Command groups

| Group | Commands |
|---|---|
| Search and verify | `search`, `verify`, `verify-many`, `character-info` |
| Lore | `book`, `lore`, `record`, `seal`, `seals` |
| Items | `item`, `find-item` |
| Transcripts | `transcript`, `character` |
| Discovery | `activity`, `event`, `coverage`, `list` |
| Meta | `stats` |

## Common filters

- `--limit`, `--offset`
- `--json`
- `--full`
- `--activity`
- `--season`
- `--event`
- `--expansion`
- `--class hunter|titan|warlock`

Filters compose. For example, a transcript search can be narrowed by activity,
season, expansion and class at the same time.

## Examples

```bash
python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "hive sword logic" --limit 10
python3 db/query.py character "Eris Morn" --limit 20
python3 db/query.py item bad-juju
python3 db/query.py find-item "Bad Juju"
python3 db/query.py transcript "Contact - Io" --speaker "Drifter" --limit 20
python3 db/query.py book "Crota"
python3 db/query.py record "Remembrance"
python3 db/query.py activity salvations-edge
python3 db/query.py event festival-of-the-lost
python3 db/query.py coverage
```

## Quote safety

Always verify before quoting:

```bash
python3 db/query.py verify \
  "If you believe your weapon wants to end all existence, then so it will." \
  --speaker "Toland the Shattered" --exact
```

Exit code `1` means the line is not canon. `--exact` requires a full canonical
line; without it, a fragment can match.

## JSON output

Add `--json` for scripts and agents. Results are compact and stable. Use
`--limit` to bound context; the API allows large limits, but agents should stay
small.

## Coverage output

`coverage` prints activities, seasons, events and gap statuses. Each row carries
`coverage_status`: `covered`, `partial_transcript`, `narration_only`,
`dialogue_source_missing`, `no_dialogue` or `missing`.

`unexplained` is empty when every zero-coverage entity has a status. A non-empty
list means a gap needs a note, not that the archive is broken.

## Exit codes

- `0` success
- `1` not found, failed verification or a failed command
- `2` invalid arguments
