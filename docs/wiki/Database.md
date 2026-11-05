# Database

## Build

```bash
python3 db/migrate.py
```

This creates `db/grimoire.db` from `source/` and `archive/`. It is a build
artifact and is not committed to git.

## Enrichment

Run enrichment after the base build, in this order:

```bash
python3 db/enrich_lore.py
python3 db/enrich_manifest.py
python3 db/enrich_seals.py
python3 db/enrich_itemsets.py --apply   # optional
```

| Step | Adds |
|---|---|
| `enrich_lore.py` | Bungie manifest lore entries and item links |
| `enrich_manifest.py` | activity catalogue, season links and manifest metadata |
| `enrich_seals.py` | seal nodes and triumph records |
| `enrich_itemsets.py` | curated armour-set classification |

Enrichment is optional for basic search, but agents and coverage reports expect
a fully enriched database.

## Integrity

```bash
bash tests/test-db.sh
```

The check covers required tables, row counts, FTS queries, HTML entity leakage,
speaker canonicalisation, provenance URLs, classification completeness and
schema version.

## Stats

```bash
python3 db/query.py stats
```

Use this to confirm the database opened and to see current row counts.

## Rebuild after source changes

```bash
python3 db/migrate.py
python3 db/enrich_lore.py
python3 db/enrich_manifest.py
python3 db/enrich_seals.py
python3 db/enrich_itemsets.py --apply
bash grimoire-master-audit.sh
```

Then regenerate documentation counts if the data changed:

```bash
python3 tests/sync-doc-counts.py
python3 tests/sync-readme-meta.py
python3 scripts/coverage-report.py
```

## Source tiers

`transcripts.source_tier` records precedence:

1. Ishtar main and tagged Commons
2. untagged Commons
3. Destinypedia
4. reviewed captions
5. auto-captions

Lower tiers are still searchable. They are not promoted to a higher tier without
a better source.

## Coverage status

Zero coverage is classified, not guessed. `coverage_notes` records
`no_dialogue`, `narration_only`, `dialogue_source_missing`,
`partial_transcript` or `unverified`, with evidence. See `docs/TAXONOMY.md`.

## Backup and release

The database is distributed as a release asset with `SHA256SUMS`. Keep a rolling
backup of the repository minus the database. Release staging:

```bash
bash scripts/release-stage.sh <version>
```
