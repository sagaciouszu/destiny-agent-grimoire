# Builds

Build identities, versions and the extraction-tier → provenance mapping for
every row in this corpus. If a row's build is not named here, the row is
wrong; do not guess one in.

## Why this page exists

Every caption, transcript and provenance row derives from a specific game
build. The caption note in `Captions.md` points here, and
`STANDARDS.md` requires every raw capture and curated row to name the build it
came from (`sunrise-pre-bl`, `build-25932352`, ...). This page is the single
registry of those builds: what they are, where they were extracted, what
state the extraction is in. Nothing in this document is aspirational - every
count was read from the live database or the extraction vault on 2026-11-10.

## Game builds

| Build ID | Bungie stamp | App release | Pkg format | Cfg version | EN baseline | Extraction status |
|---|---|---|---|---|---|---|
| `sunrise-pre-bl` | `86657.20.08.23.1800.d2_rc` | Destiny 2: Shadowkeep / Season of Arrivals era (~Sep 2020 build) | Tiger `.pkg`, package version **38** | not recorded | EN-only | Extracted 2026-11-07/08 (1,709 `.pkg` files, verified); the extraction vault is private and not part of this repository. Caption corpus reconciled into Grimoire (1,106 tables / 9,282 lines). Extraction prior art, released as v0.29.0+. |
| `build-25932352` | `245114.26.10.13.2000.v500_live.main` | Update **9.7.0.6** (Oct 20 2026), Steam buildid **25932352**, appid 1085660 | Tiger `.pkg`, package version **53** (layout differs from v38: entry table at `0x44`, `pkg_id` at `0x10`, `file_size` at `0x120`; tables byte-layout compatible) | not recorded | EN-only | Container verified from the installed Steam copy (2,498 files, 162,825,758,961 B; `destiny2.exe` sha256 `fe69488d…c305cfb`); the extraction vault is private. `w64_sr_globals_*` StringBanks are cleartext UTF-8 (class `0x808099f1`); **15 of 16 packages ingested** (8,597 English entries). `0134` is skipped: its entries use non-StringBank classes (`0x80809a81`, `0x80809b23`), so the `0x808099f1` resolver correctly finds 0 tables. |

Manifest note: the Bungie manifest stamp `245114.26.10.13.2000-1-bnet.66137`
corresponds to the same content build (same prefix, fetched via Bungie API
2026-11-04). Provenance naming for the live tier: `source_build='build-25932352'`,
taxonomy `monument-of-triumph`.

## Extraction tiers

Counts read from the live `db/grimoire.db` on 2026-11-10 (9,229 transcript
headers, 125,324 lines, `caption_provenance` 56,119 rows, `caption_sightings`
63,359 rows).

| Tier (`source_tier`) | Rows (headers / lines) | Build / source |
|---|---|---|
| `game_caption` | 7,911 / 55,678 | Two builds. `sunrise-pre-bl`: 1,106 / 9,282 from committed `archive/data/captions.jsonl`. `build-25932352`: 6,805 / 46,396 from `archive/data/captions-live.jsonl` (15 packages, 46,512 provenance rows; 116 of them attach to pre-existing non-caption lines). |
| Web transcripts, `ishtar-collective.net` (Ishtar Collective, archival primary, human-verified) | 1,271 pages total: `ishtar_web` 1,129 / 15,850 lines · `ishtar_main` 101 / 4,203 · `ishtar_commons` 26 / 354 · `published` 8 / 22 · `validated` 7 / 22 | Web captures, era-scoped; primary source for DCV-era (vaulted) content. Not build-derived. |
| `destinypedia` | 10 / 981 | Verbatim from the Destinypedia wiki (front-matter `Tier: destinypedia`). Destinypedia is corroboration per the source hierarchy in `STANDARDS.md`, not the primary. |
| `youtube_captions` | 6 / 638 | YouTube-caption-derived; speaker labels reviewed where noted in the source file (e.g. `partial-expedition` lists 26 sources, "speaker labels reviewed"). Not build-derived. |
| `cutscene` (cutscene captions) | 31 / 47,576 | Curated cutscene transcripts from YouTube cutscene compilations; rows carry speaker `Cutscene` or stage notes, never invented speaker labels. Not build-derived. |

`books`, `records`, `cards` and `lore_entries` derive from the same web/manifest
sources and carry the same provenance discipline; they are out of scope for
this page. See `Database.md` for structure and
`STANDARDS.md` (Source hierarchy) for precedence.

## Provenance chain, worked example

`caption-w64-investment-globals-client-0709-7898` (live DB, `game_caption`,
EN, `sunrise-pre-bl`):

1. Slug decodes as package base `w64_investment_globals_client_0709` +
   StringReference entry index `7898`.
2. `transcript_lines`: 7 lines, table title "Game caption (dialogue)", all
   speaker `Cutscene` (the 2019 build has no per-line speaker for this table).
3. `caption_provenance`: one row per line - `kind='dialogue'`,
   `source_pkg='w64_investment_globals_client_0709'`, `source_entry='7898'`,
   `bank_entry='7885'`, StringReference hashes attached per line.
4. `source_build='sunrise-pre-bl'` (every record in `archive/data/captions.jsonl`
   carries it; nothing mixes builds silently).

What `build-25932352` carries instead: the same logical text lives in a v53
StringBank package (`w64_sr_globals_*`, class `0x808099f1`); the build exposes
no per-line StringReference hash for these banks, so identity is
`(source_pkg, bank_entry, record_index, record_part)`. `source_build` is
`build-25932352`; package offsets and entry/block layout differ from v38, but
the StringBank payload is cleartext UTF-8. Nothing is re-hashed or guessed.

Live worked example: `caption-live-0294-5234-dialogue` is built from entry 5234
of `w64_sr_globals_0294`; each line records the bank entry, the record slot,
the paragraph part and the build. `source_pkg` keeps the full package name
with its patch suffix (`_0294`), not the family stub. Chapter ownership and
verification flow: `Captions.md`.

## What the 2026 build unlocks

Honest status of `build-25932352` (probe report 2026-11-09; single-table proof, tier audit and post-fix addenda
are in the private extraction vault, not this repository):

- **Container layer verified.** v53 layout decodes byte-exactly on 2,417/2,417
  packages. The local extraction copy is byte-identical to the Steam install.
- **StringBank text is not encrypted.** The earlier "rotated AES-GCM keys"
  verdict applies to encrypted block classes, not to the `w64_sr_globals_*`
  StringBanks: `0x808099f1` entries decode as cleartext UTF-8 with the
  `tiger-pkg` unpacker plus `liboodle-data-shared.so`.
- **Layers are mounted, not guessed.** A package family ships a base (`_0`)
  plus patch layers. Across the 15 ingested families that is 1,158 entries
  added, 146,986 overlaid and 636 class replacements; for `0294` alone, 1,158
  entries overlay and 13 change class. `scripts/merge-pkg-layers.py` produces
  the mounted view. Patched text is current-build text (`Gambit Ops`,
  `Buildcraft Stakes`); base-only extraction is stale and is not shipped.
- **15 of 16 packages are ingested.** 8,597 English entries, 153,558 strings,
  51,737 package-local lines -> 51,735 after the global containment pass
  (cross-package repeats retained) -> 46,512 live provenance rows (11,678 `dialogue`, 26,945 `narration`, 7,889
  `objective`) and 46,396 caption lines. 257 named speakers, every one from a
  quoted `"..." —Name` attribution. Every row traces to
  `(package, entry, record, part, build)`.
- **Coverage is honest, not total.** 4,442 of 8,597 English entries (52%)
  contribute at least one kept line; 3,588 yield nothing after filtering.
  `w64_sr_globals_0134` has no English string-bank entries and is skipped.
- **Filters are deliberate.** 122,528 short labels/UI headings, 6,723 noise
  strings, 5,231 duplicates, 13,949 item-text fragments and 1,378 mechanical
  perk/modifier lines were dropped. The per-package counts ship in
  `archive/data/locale-maps/<package>.stats.json`.
- **Locale resolution is conservative.** `scripts/resolve-locales.py` emits an
  entry only when its table is pinned by at least two independent script
  anchors and reproduces `0294`'s verified EN list exactly (634/634, zero
  false positives). Two packages resolve `high`, 13 `medium` (one or more
  unanchored tables skipped and logged); nothing is guessed.
- **Language gate.** `scripts/validate-live-language.py` rejected six German
  tables in `w64_sr_globals_029e` (the resolver had placed them on English
  slots). The shipped tier has 0 Cyrillic, 0 CJK and 0 Polish-diacritic lines;
  23 German-diacritic hits are English proper nouns (`Häkke`, `Jötunn`).
- **Independent English check.** `scripts/verify-live-english.py` scores
  slots against a lexicon built from the corpus's existing English canon, not
  the resolver's stopword lists. 40 tables per package across all 15 packages:
  English median 0.897–0.936, translated siblings 0.000–0.079, **0 flags**.
- **Schema 1.11.0** (`db/SCHEMA_VERSION`): removes seven unused
  normalized-text indexes (`book_entries`, `grimoire_cards`, `interactions`,
  `items`, `records`, `character_lines`, `lore_entries`); `transcript_lines`
  keeps its normalized index for caption dedupe joins. The shipped database is
  about 30 MiB smaller with no content change.
- **Speaker fold survives rebuilds.** `The Queen` canonicalizes to `Mara Sov`,
  matching the fold already present in the shipped corpus (37 lines across 11
  transcripts); without the alias a fresh rebuild lost their attribution links.
- **Schema 1.10.0** (`db/SCHEMA_VERSION`): adds `v_canon_speakers` (230
  persona-canon speakers; `v_speakers` remains the 423-row discovery view).
- **Schema 1.9.0** (`db/SCHEMA_VERSION`): `caption_provenance.record_index`
  and `record_part` join `source_build`/`source_pkg`/`bank_entry`, and
  `caption_sightings` logs every processed record line
  (`line_id`, `source_build`, `source_slug`, `line_ord`).
- **Two provenance layers.** `caption_provenance` is one row per line (the
  current index). `caption_sightings` is the observation log: 63,359 rows,
  including 7,681 merged lines and every cross-package repeat that the current
  index cannot hold. `source_slug` + `line_ord` is the identity, so sunrise
  lines that share a bank entry are not collapsed.
- **Class `0x808099ef` is not text.** 8,656 entries across 13 packages carry
  hash/reference tables (120–2,460 B, zero ASCII word runs); `0294/5892` is one
  of them and stays skipped. Evidence:
  `archive/data/locale-maps/class-808099ef.skip.json`.

`build-25932352` is legitimate for current-era extraction and verification,
never as ground truth for what an earlier expansion shipped.

## Refreshing the live tier

The live build is refreshed by one script, not by hand:

```bash
python3 scripts/refresh-live-build.py \
  --source /path/to/build-<id> --version "<bungie stamp>" --dry-run
```

It unpacks every `w64_sr_globals` layer, merges the layers, resolves locales,
extracts English, validates language, combines, writes a drift report, registers
the build in `archive/data/builds.json`, rebuilds and runs the gates.

- A new build is written to `archive/data/live-builds/<build>.jsonl` with
  **build-scoped slugs**; the current build stays in
  `archive/data/captions-live.jsonl`.
- `db/migrate.py` loads both, so a changed line becomes a new
  `caption_sightings` row, never an inline rewrite of an earlier build.
- Running against the registered current build is a **no-op** (exit 0).
- `--dry-run` plans every stage and writes nothing; `--self-test` proves the
  drift report names a changed line (including punctuation-only changes).
- Source identity: `destiny2.exe` sha256 is checked before and after extraction,
  `--expected-sha256` can pin it, and the hash is recorded in the build note.
- A failed gate rolls back `builds.json` and the new tier file; a refused
  `--force` on the current build prevents duplicate sightings.
- Drift compares against the latest registered build, not always the original
  current file.
- After a successful rebuild the script exports site stats, syncs doc counts and
  runs the docs-consistency gate.
- A build whose English tables cannot be resolved is skipped and logged, not
  guessed.

## Non-goals / out of scope

- **Cinematics never carry speaker labels.** They are excluded by Bungie's own
  implementation; the standard mirrors that exclusion (`STANDARDS.md`, corpus
  scope). Attribution for cinematics is `speaker='Cutscene'` plus provenance,
  never a guessed speaker.
- **Investment/item mirrors are excluded** from the gameplay-caption tier by
  rule (in sunrise they were 8,983 of 11,699 VO rows, all `w64_investment_*`;
  in the live build the class pair is segregated: `0x8080799d` vs the
  `0x808099f1/ef` globals pair). Item/quest prose is never VO.
- **Era/parlance drift is not a canon rewrite.** `STANDARDS.md` is verbatim:

  > **A build is not a proxy for an earlier build.** The live client is the
  > current game with years of Bungie changes on top of its content: recast
  > voices, rewritten lines, moved items and dropped activities. Text that
  > differs from an earlier era's capture is drift, not an error — canon lines
  > alike keep the era capture text; the drift log is the record, never an
  > inline rewrite. The live build (`build-25932352`) is legitimate for
  > current-era extraction, 2024+ gameplay labels and verification, never as
  > ground truth for what Beyond Light shipped.

  Rewriting era canon to match the live build, or vice versa, requires owner
  approval; it is never an inline edit.
- **Captions are not persona canon** (`STANDARDS.md` §Caption contract, §10):
  persona counts are unaffected by captions.
- This page registers builds and tiers; it does not re-document caption rules
  (`Captions.md`) or schema (`Database.md`).
