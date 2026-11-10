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
| `build-25932352` | `245114.26.10.13.2000.v500_live.main` | Update **9.7.0.6** (Oct 20 2026), Steam buildid **25932352**, appid 1085660 | Tiger `.pkg`, package version **53** (layout differs from v38: entry table at `0x44`, `pkg_id` at `0x10`, `file_size` at `0x120`; tables byte-layout compatible) | not recorded | EN-only (45 `_en` VO files; no other locales present) | Phase 1 probe complete 2026-11-09 (`/opt/vault/d2-bl-extract/reports/build-25932352-probe.md`). Copy at `/opt/vault/d2-bl-extract/build-25932352` (2,498 files / 2,417 `.pkg`, 162,825,758,961 bytes, matches Steam install). **No captions extracted yet** - content is encrypted with rotated keys; see "What the 2026 build unlocks". |

Manifest note: the Bungie manifest stamp `245114.26.10.13.2000-1-bnet.66137`
corresponds to the same content build (same prefix, fetched via Bungie API
2026-11-04). Provenance naming for the live tier: `source_build='build-25932352'`,
taxonomy `monument-of-triumph`.

## Extraction tiers

Counts read from the live `db/grimoire.db` on 2026-11-09 (2,424 transcript
headers, 78,928 lines, `caption_provenance` 9,607 rows).

| Tier (`source_tier`) | Rows (headers / lines) | Build / source |
|---|---|---|
| `game_caption` | 1,106 / 9,282 | `sunrise-pre-bl` (EN). Committed corpus `archive/data/captions.jsonl` (69 records, all `source_build='sunrise-pre-bl'`; 1,106 loaded as `source_tier='game_caption'`). `build-25932352` pending extraction. |
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

What `build-25932352` would carry instead: the same logical table lives in a
v53 package (e.g. the `w64_investment_globals_client_*` family, split by the
patch model); `source_build='build-25932352'`; package offsets, entry/block
layout and the def-hash namespace all differ (v53: entry table at `0x44`, not
`0x110`), so the StringReference hashes would have to be re-derived after
decryption - the hash scheme for the live build is **TBD, not the v38 scheme**.
Nothing from the 2026 build is in the caption tier yet. Chapter ownership and
verification flow: `docs/wiki/Captions.md`.

## What the 2026 build unlocks once parsed

Honest status of `build-25932352` (probe report 2026-11-09,
`/opt/vault/d2-bl-extract/reports/build-25932352-probe.md` and
`EXTRACTION_MISSION.md`):

- **Container layer verified.** v53 layout decodes byte-exactly on 2,417/2,417
  packages (`file_size@0x120` matches actual size everywhere; entry/block
  tables parse on every sampled file; SHA-1 block hashing verifies).
- **Zero pre-BL-usable text blocks.** The pre-BL AES-GCM keys/nonce fail
  211/211 sampled blocks across ~50 families; `flags==1` (Oodle-only) blocks
  do not exist; every text-relevant block is `flags==3` or `flags==7`
  (encrypted). No plaintext def payloads exist to shortcut identification.
  The def-hash namespace fully rotated (`0x80809A88/8A` and the BL+ narrator
  marker `0x80809733` are 0-occurrences).
- **Narrator neighborhood candidate.** `0x80809738` (1,158 entries in
  `sr_*`, 44.7% of `sr_audio`, 45.6% of `sr_dialog`; mean ~100 B, `0x54`
  modal) is the live candidate for the BL+ audio-narrator def class - the
  audio packages now co-locate `0x808099f1` string-bank-class refs, absent in
  sunrise's audio families. **Content level: UNVERIFIED.** No speaker name
  can be quoted from this build until Gate 0 (live AES-GCM keys) clears.
- **2024+ speaker-name gameplay subtitles precedent.** Per `STANDARDS.md`,
  the live build's gameplay speaker-name subtitles are accepted as attribution
  *with provenance* (`speaker_source` naming the build), gameplay subtitles
  only, never for cinematics, never as persona canon.
- **Schema bump.** Schema is now **1.7.0** (`db/SCHEMA_VERSION`): a `builds`
  registry table and `caption_provenance.source_build` ship in this release;
  future caption rows trace back to a build.
- **Gate 0 / Phase 2.** Phase 2 (EN caption extraction,
  `reports/build-25932352-vo.md`) cannot start until the live keys/nonce
  schedule are obtained; the probe's risk-ordered opening move is
  `w64_sr_globals_0548_*` → `client` → `investment` → `ui` →
  crucible/kepler/s25/planet → dialog/audio → cinematics/video last.

Milestones are exactly those in the two documents above; none of the above is
a shipped release. No milestone beyond the probe exists.

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
