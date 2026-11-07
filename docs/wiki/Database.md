# Database

## Build

```bash
python3 db/migrate.py
```

This creates `db/grimoire.db` from `source/` and `archive/`. It is a build
artifact and is not committed to git. The build also loads
`archive/data/captions.jsonl` (game captions, see
[Game captions](#game-captions)).

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

1. Ishtar main-site (`ishtar_main`, `ishtar_web`) and tagged Commons
2. untagged Commons
3. Destinypedia
4. reviewed captions
5. auto-captions

`game_caption` sits outside that ladder: English subtitle and callout text
extracted from the local game build (see [Game captions](#game-captions)). It
is ground-truth game text, but it carries no section curation and only the
speaker attribution the caption pass reviewed, so it never outranks a curated
transcript for attribution.

Lower tiers are still searchable. They are not promoted to a higher tier without
a better source.

## Game captions

`migrate.py` loads `archive/data/captions.jsonl` (committed, curated: English
lines, speaker attribution, activity facets, dedup verdicts, build
`sunrise-pre-bl`) as `source_tier='game_caption'`, `lang='en'`.

- **No duplicate text.** A caption line whose normalized text already exists in
  canon is not inserted again; its StringReference hash and package origin
  attach to the existing line in `caption_provenance` instead. Search therefore
  never returns the same line twice, and no second attribution is introduced.
- **Facets are curated, never guessed.** The activity keyword verdict from the
  extraction pass is stored as `confidence='derived'` (season/expansion filled
  from the activity catalogue, exactly as `classify()` would). Everything else
  stays `unknown` - caption text spans every era, so no season is inferred.
- **Speakers come from five verified sources, never from guessing:**
  (1) the curated activity announcer (one narrator per activity - this *is*
  the build's model: no per-line speaker exists for callouts);
  (2) cross-attribution, where a caption line's normalized text already exists
  in canon with exactly one speaker; (3) the `0x80808d54` dialogue-node def,
  which stores a per-line FNV-1 speaker hash for vendor/quest greetings
  (`speaker_source='dialogue_node'`, 12 lines); (4) inline `[Petra]` prefixes
  (`speaker_source='line_prefix'`, prefix moved into the speaker column so the
  line stays quoteable); (5) **Ishtar/web transcript containment**
  (`speaker_source='ishtar_containment'`, 180 lines) - a caption line that is a
  substantial fragment (>=50% of the longer string) of a *spoken* canon line
  with exactly one speaker inherits it. The ratio guard is what stops a short
  quote inside long lore prose from being mis-attributed. Cutscenes, mission
  dialogue, ambient NPC pools and callouts carry **no per-line speaker in this
  build** - recorded as an honest gap. Full evidence:
  `/opt/vault/d2extraction/SPEAKER_ATTRIBUTION.md`.
- **Table-level exclusion is per line, not per table.** Real speech shares
  tables with lore paragraphs and objective text, so the extraction pass keeps
  the spoken lines out of a table it otherwise classifies as `long_text` /
  `objective` (75 lines recovered from 12 such tables). On-screen labels are
  kept: they are rendered captions and carry personality.
- **Investment-package lines were audited, not dropped:** 8,983 of the lines
  come from `w64_investment_*`; 1,724 of those already exist in
  `items`/`records`/`book_entries`/`grimoire_cards` (deduped by the normal
  canon rule), the rest are quest/item prose and labels that the game renders
  on screen.
- **Stat/scoreboard lines stay complete but demoted** (`speaker='Narration'`,
  `is_stage_dir=1`), so they rank with other stage directions.
- **Search surface:** `--type captions` (fts `source='caption'`), `--lang`
  (every row is `en` today), and the activity facets (`--activity gambit`,
  `crucible`, `trials-of-osiris`, `trials-of-the-nine`, `menagerie`).
  Ranked search gives caption rows a -1.0 boost; stage-direction penalties still
  apply on top.
- **Persona canon excludes captions**: `persona.json` `canon_lines` counts the
  corpus a persona was built from, so a caption drop never rewrites an agent
  persona (see STANDARDS.md "Persona canon").
- **Gate:** `tests/caption-test.py` (registered in `grimoire-master-audit.sh`).

### Adding a language later

Languages are a data drop, not a schema change: `transcripts.lang` and
`fts.lang` already exist and `api.search(lang=...)` already filters.

1. Extract the language with the caption pipeline into a sibling JSONL with
   `lang` set per record (for example `captions_ja.jsonl`), same curation keys,
   slug suffixed with the language so headers stay unique.
2. Point `load_captions()` at the extra file(s); insertions are additive.
3. Copy the English counterpart's `transcript_classification` row (identical
   content - do not re-derive) and keep `caption_provenance` per line.
4. Re-run the full build sequence, `tests/caption-test.py`, the pinned corpus
   counts in `tests/query-interface-test.sh` (activity line counts move) and
   `python3 tests/sync-doc-counts.py`.
5. Re-evaluate `tests/test-db.sh`'s "unknown classification below 50%" gate
   with explicit approval before shipping: caption rows are honestly `unknown`
   by design, so a second language pushes the share past 50%. The fix is to
   re-scope that gate (for example to non-caption transcripts), never to invent
   classifications to satisfy a ratio.

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
