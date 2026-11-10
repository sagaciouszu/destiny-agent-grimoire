# Captions

Build identities and the tier -> provenance mapping: [`docs/wiki/Builds.md`](Builds.md).

English captions extracted from local game builds: `sunrise-pre-bl` (Season of
Arrivals, 2020) and `build-25932352` (the live build as of 2026-10/11). Every
caption row names the build it came from via the slug/`source_build`
field; nothing mixes builds silently. `source_tier='game_caption'`,
`lang='en'`. Everything here is validated by tests; nothing in this document is
aspirational.

## Sources & provenance (canonical)

Every English line lives on exactly one caption table. `migrate.py` loads
`archive/data/captions.jsonl` (committed, one record per caption table) as
`source_tier='game_caption'` `lang='en'`.

- **No duplicate text.** If the normalized text of a caption line already
  exists in canon, the line is not inserted a second time; the caption
  table's StringReference hash/package attaches to the existing canon line
  via `caption_provenance` (one row per *line*, never two for the same text).
  Search never returns the same text twice.
- **Every observation is retained.** `caption_sightings` records each
  processed record line (`source_slug` + `line_ord`), including lines whose
  provenance was claimed by an earlier build and repeats across packages. The
  two layers answer different questions: provenance = what the line is now,
  sightings = everywhere it has been seen.
- **Attribution provenance is stored, not dropped.** `transcript_lines.speaker_source`
  holds how the speaker for an attributed caption line was attached; the
  caption loader re-adopts it on canon twins only when their own field is NULL.
  Values: `build-25932352`, `ishtar_containment`, `dialogue_node`,
  `line_prefix`. Present on 4,214 rows (4,054 live + 131 + 27 + 2).
- **`speaker_source IS NULL`** only for lines the build never attributes
  (`speaker='Cutscene'` / `'Narration'` / store names). Never author one in
  prose; tests reject it for speaker_source IS NULL lines whose speaker is
  attributed.
- **Activity facets are curated, never guessed.** The activity keyword verdict
  is stored as `confidence='derived'` with season/expansion filled from the
  activity catalogue (exactly `classify()` behaviour).
- **No per-line speaker exists for callouts or mission dialogue in the 2019
  build.** `0x80808d54` holds a FNV-1 speaker hash only on the 2019 vendor-desk
  greetings; `build-25932352` (2024+ client) adds gameplay speaker-name
  subtitles, which are accepted with provenance (`speaker_source` naming the
  build) and never apply to cinematics. Any attempt to add per-line speakers
  elsewhere is fabricated attribution and tests reject it).
- **The 12 vendor-desk lines** are the maximum statically resolvable set
  under `0x80808d54` (Ikora 7, Zavala 3, Devrim 1, Sloane 1); everything else
  like `Speaker`/`Narration` is an *audit trail* of the absence of a build-
  side attribution mechanism, not a gap in enforcement.

## Live-build string banks (`build-25932352`)

The live client has no separate subtitle package for this text. English lives
inside `w64_sr_globals_*` StringBank entries, thirteen locales per logical
table, cleartext UTF-8. Fifteen of sixteen packages are ingested from
`archive/data/captions-live.jsonl`, one record per `(package, entry, kind)`;
repeated text across packages keeps a separate record and sighting.
`w64_sr_globals_0134` has no English string-bank entries.

| property | value |
|---|---|
| provenance | `caption_provenance.source_build='build-25932352'`, 46,512 rows |
| sightings | `caption_sightings` 63,359 rows total; one per processed record line |
| line identity | `source_pkg` + `bank_entry` + `record_index` + `record_part` (the build exposes no per-line StringReference hash, so `hash` is NULL) |
| `kind` | 11,678 `dialogue`, 26,945 `narration`, 7,889 `objective` — heuristic, from punctuation and in-string attribution |
| speaker | only from a quoted `"..." —Name`; 257 named speakers; everything else `Cutscene` |
| season/act | never inferred |

**Excluded by design:** short labels and UI headings (122,528), mechanical copy
(perk and modifier stat text, 1,378), item-text fragments (13,949), noise
strings (6,723) and package-local duplicates (5,231). Cross-package repeats
(1,229 lines) are **kept**: the loader collapses the text to one canon line and
`caption_sightings` records each package that carried it. Each package's
drop/keep counts ship as a stats sidecar.

**English selection.** Locale is positional, not an in-file field. The English
entry list for each package is committed under `archive/data/locale-maps/` and
comes from `scripts/resolve-locales.py`, which emits an entry only when its
table is pinned by at least two independent script anchors. It reproduces
package `0294`'s content-verified list exactly (634/634); two packages resolve
`high`, 13 `medium` with unanchored tables skipped and logged.
`scripts/validate-live-language.py` then rejects whole tables whose aggregate
text is another language (six German tables in `029e`).
`scripts/verify-live-english.py` independently scores sampled slots against a
lexicon built from existing English canon and compares them with translated
siblings; 40 tables per package across all 15 packages pass with English
medians of 0.90+ and no flags. A package or table that cannot be verified is
skipped and logged, never guessed.

**Merged lines.** `caption_provenance` keeps the first build's row; the later
sighting is stored in `caption_sightings` (7,681 merged lines today, including
1,651 live lines that repeat 2020 canon and 3,572 cross-package repeats). No
observation is lost; a query that wants every build must read the sightings
table, and a query that wants the current index reads provenance.

## Captions dedup vs persona canon (exact rule)


Persona canon EXCLUDES caption lines: `persona.json` `canon_lines` counts lines
with `source_tier != 'game_caption'`. This is a hard predicate, enforced by
`persona-freshness.py`, `count-consistency.py`, `tests/caption-test.py`,
`character_info.spoken_lines`, and the agent template's persona generator.
Adding speakered captions never makes agents "more fluent"; it makes them
wronger about what Eris/Drifter says, which is why the gate exists.

## Exclusion rules (which caption tables drop out)

`non_subtitle_tables.json` holds ~2.4k tables (`objective`, `long_text`,
`item`, `ui`). These are rendered menu/quest/lore text, never voiced audio;
the line-level heuristic correctly identifies them as narrative prose, not
captions. Any document that presents them as dialogue is wrong; tests and
docs-audit enforce keeping them out.

## Verification

`tests/caption-test.py` asserts:

- every caption header is tagged, English, and has a taxonomy row,
- every caption line keeps StringReference provenance (no orphans, no
  duplicate provenance rows),
- caption text is never duplicated vs canon,
- activity facets are curated (`derived`) and their vocabulary resolves to
  taxonomy slugs,
- FTS and the verification index mirror the caption lines exactly,
- stage direction / stat lines stay demoted,
- persona canon counts exclude captions.

## Related reading

- `docs/wiki/Database.md` — structure, schema, FTS, verification flow
- `SPEAKER_ATTRIBUTION.md` (extraction vault) — line-by-line evidence trail
- `tests/caption-test.py` — the normative definition of correct captions
