# Builds

Build identities, versions and the extraction-tier → provenance mapping for
every row in this corpus. If a row's build is not named here, the row is
wrong; do not guess one in.

## Why this page exists

Every caption, transcript and provenance row derives from a specific game
build. The wiki's caption note in `docs/wiki/Captions.md` points here, and
`STANDARDS.md` requires every raw capture and curated row to name the build it
came from (`sunrise-pre-bl`, `build-25932352`, ...). This page is the single
registry of those builds: what they are, where they were extracted, what
state the extraction is in. Nothing in this document is aspirational - every
count was read from the live database or the extraction vault on 2026-11-09.

## Game builds

| Build ID | Bungie stamp | App release | Pkg format | Cfg version | EN baseline | Extraction status |
|---|---|---|---|---|---|---|
| `sunrise-pre-bl` | `86657.20.08.23.1800.d2_rc` | Destiny 2: Shadowkeep / Season of Arrivals era (~Sep 2020 build) | Tiger `.pkg`, package version **38** | not recorded | EN-only | Extracted 2026-11-07/08 → `/opt/vault/games/sunrise` (~74 GB, 1,709 `.pkg` files, verified). Caption corpus reconciled into Grimoire (1,106 tables / 9,282 lines). Extraction prior art, released as v0.29.0+. |
| `build-25932352` | `245114.26.10.13.2000.v500_live.main` | Update **9.7.0.6** (Oct 20 2026), Steam buildid **25932352**, appid 1085660 | Tiger `.pkg`, package version **53** (layout differs from v38: entry table at `0x44`, `pkg_id` at `0x10`, `file_size` at `0x120`; tables byte-layout compatible) | not recorded | EN-only | Container verified and byte-identical copy at `/opt/vault/d2-bl-extract/build-25932352` (2,498 files, 162,825,758,961 B; `destiny2.exe` sha256 `fe69488d…c305cfb`). `w64_sr_globals_*` StringBanks are cleartext UTF-8 (class `0x808099f1`); package `w64_sr_globals_0294` (**634 EN entries**) is extracted and ingested. The other 15 globals packages are pending extraction. |

Manifest note: the Bungie manifest stamp `245114.26.10.13.2000-1-bnet.66137`
corresponds to the same content build (same prefix, fetched via Bungie API
2026-11-04). Provenance naming for the live tier: `source_build='build-25932352'`,
taxonomy `monument-of-triumph`.

## Extraction tiers

Counts read from the live `db/grimoire.db` on 2026-11-10 (2,936 transcript
headers, 82,249 lines, `caption_provenance` 12,934 rows).

| Tier (`source_tier`) | Rows (headers / lines) | Build / source |
|---|---|---|
| `game_caption` | 1,618 / 12,603 | Two builds. `sunrise-pre-bl`: 1,106 / 9,282 from committed `archive/data/captions.jsonl`. `build-25932352`: 512 / 3,321 from `archive/data/captions-live.jsonl` (package `w64_sr_globals_0294`, 3,327 provenance rows, 6 of them attached to pre-existing non-caption lines). |
| Web transcripts, `ishtar-collective.net` (Ishtar Collective, archival primary, human-verified) | 1,236 pages total: `ishtar_web` 1,129 / 15,850 lines · `ishtar_main` 101 / 4,203 · `ishtar_commons` 26 / 354 · `published` 8 / 22 · `validated` 7 / 22 | Web captures, era-scoped; primary source for DCV-era (vaulted) content. Not build-derived. |
| `destinypedia` | 10 / 981 | Verbatim from the Destinypedia wiki (front-matter `Tier: destinypedia`). Destinypedia is corroboration per the source hierarchy in `STANDARDS.md`, not the primary. |
| `youtube_captions` | 6 / 638 | YouTube-caption-derived; speaker labels reviewed where noted in the source file (e.g. `partial-expedition` lists 26 sources, "speaker labels reviewed"). Not build-derived. |
| `cutscene` (cutscene captions) | 31 / 47,576 | Curated cutscene transcripts from YouTube cutscene compilations; rows carry speaker `Cutscene` or stage notes, never invented speaker labels. Not build-derived. |

`books`, `records`, `cards` and `lore_entries` derive from the same web/manifest
sources and carry the same provenance discipline; they are out of scope for
this page. See `docs/wiki/Database.md` for structure and
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
verification flow: `docs/wiki/Captions.md`.

## What the 2026 build unlocks

Honest status of `build-25932352` (probe report 2026-11-09,
`/opt/vault/d2-bl-extract/reports/build-25932352-probe.md`; single-table proof
and tier audit under the same vault):

- **Container layer verified.** v53 layout decodes byte-exactly on 2,417/2,417
  packages. The copy in the vault is byte-identical to the Steam install.
- **StringBank text is not encrypted.** The earlier "rotated AES-GCM keys"
  verdict applies to encrypted block classes, not to the `w64_sr_globals_*`
  StringBanks: `0x808099f1` entries decode as cleartext UTF-8 with the
  `tiger-pkg` unpacker plus `liboodle-data-shared.so`. Package `0294` proves
  the path: 634 EN entries, 17,990 strings, 0 parse failures.
- **One package is ingested.** `w64_sr_globals_0294` contributes 3,327 live
  provenance rows (736 `dialogue`, 1,823 `narration`, 768 `objective`; 38 named
  speakers, all from in-string attribution). Every row traces to
  `(package, entry, record, part, build)`.
- **Filters are deliberate.** 13,614 short labels/UI headings, 1,503 noise
  strings, 245 duplicates, 911 item-text fragments and 91 mechanical
  perk/modifier lines were dropped; 259 of 634 entries yielded no kept line.
  The per-package counts ship in
  `archive/data/locale-maps/w64_sr_globals_0294.stats.json`.
- **Locale resolution is verified, not guessed.** `scripts/resolve-locales.py`
  reproduces the content-verified EN entry list for package `0294` exactly
  (634/634, zero false positives). The other 15 globals packages need
  extraction before they can be resolved; a package that cannot be pinned by
  two independent script anchors is skipped and logged.
- **Schema bump.** Schema is now **1.8.0** (`db/SCHEMA_VERSION`):
  `caption_provenance.record_index` and `record_part` join
  `source_build`/`source_pkg`/`bank_entry`.
- **Known limit.** `caption_provenance` is one row per line. Where the live
  build repeats text the 2020 build already shipped, the row keeps
  `sunrise-pre-bl`; the live sighting is logged in the audit, not stored as a
  second row. 157 emitted live lines merged into existing canon this way (6 of
  them onto non-caption web lines).

`build-25932352` is legitimate for current-era extraction and verification,
never as ground truth for what an earlier expansion shipped.

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
  > alike keep the era capture text; a drift log is the deliverable, never an
  > inline rewrite. The live build (`build-25932352`) is legitimate for
  > current-era extraction, 2024+ gameplay labels and verification, never as
  > ground truth for what Beyond Light shipped.

  Rewriting era canon to match the live build, or vice versa, requires owner
  approval; it is never an inline edit.
- **Captions are not persona canon** (`STANDARDS.md` §Caption contract, §10):
  persona counts are unaffected by captions.
- This page registers builds and tiers; it does not re-document caption rules
  (`docs/wiki/Captions.md`) or schema (`docs/wiki/Database.md`).
