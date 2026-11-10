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
- **Attribution provenance is stored, not dropped.** `transcript_lines.speaker_source`
  holds how the speaker for an attributed caption line was attached; the
  caption loader re-adopts it on canon twins only when their own field is NULL.
  Values: `ishtar_containment`, `dialogue_node`, `line_prefix`. Schema 1.5.0
  records provenance for every attributed caption line (206 rows: 180 +
  12 + 2 initially committed).
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
table, cleartext UTF-8. It is ingested from
`archive/data/captions-live.jsonl`, one record per `(entry, kind)`.

| property | value |
|---|---|
| provenance | `caption_provenance.source_build='build-25932352'` |
| line identity | `source_pkg` + `bank_entry` + `record_index` (the build exposes no per-line StringReference hash, so `hash` is NULL) |
| `kind` | `dialogue`, `narration`, `objective` — heuristic, from punctuation and in-string attribution |
| speaker | only from `"..." —Name` inside the string; everything else `Cutscene` |
| season/act | never inferred |

**Excluded by design:** short labels and UI headings, mechanical copy (perk and
modifier stat text), and lines that are fragments of an `items` entry the
corpus already holds. The extractor reports each drop count per package so the
gap is visible rather than hidden.

**Known limitation.** `caption_provenance` is one row per line. If the live
build repeats text the 2020 build already shipped, the row keeps
`sunrise-pre-bl` and the live sighting is not stored. The drift log, not this
table, is where a second-build sighting is recorded.

**English selection.** Locale is positional, not an in-file field. The English
entry list for each package is committed under
`archive/data/locale-maps/` and was derived from a content-verified locale
pass; a package whose English entries cannot be verified is skipped and logged
rather than guessed.

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
