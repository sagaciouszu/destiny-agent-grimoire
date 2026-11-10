# Beyond Light → Renegades — coverage record

**Status:** historical record of what was extracted and what remains visible.
This page is not a plan and does not track the current live build.

## Builds referenced

`sunrise-pre-bl` (2020) and `build-25932352` (Update 9.7.0.6, Oct 2026), Steam
appid 1085660, v53 container, AES-wrapped. The private probe report
(`build-25932352-probe.md`) is not distributed.

## Extracted-data notes

- 2,417 `.pkg` files on disk, matching the Steam install byte-for-byte.
- `w64_sr_globals_0294_0` carries multi-locale name tables: enemies (Nightmare /
  Scorn / Remnant tiers), feats and buffs, and placeholders. Files are
  one-per-locale per table type; `0_` = ES, `1_` = IT, `24_` = FR, and the
  `29_`/`60_`/`125_`/`151_` sets are EN. Rows are one concatenated text table per
  file with stable byte offsets.
- `w64_sr_dialog_*_en_*.pkg` packages carry the VO-side descriptor data
  (`0x8080bca8`, about 8k entries per package, paired to Wwise `t26/t6`). They
  contain no English text; NPC names are FNV-1 hashes into `sr_globals`.
- `sr_globals` is shared across all six locales: one header file yields six
  locales' name tables together.

## Beyond Light coverage at v0.36.0

Beyond Light-era source entries on the Ishtar timeline: 72 (30 BL proper +
Hunt 5 + Chosen 13 + Splicer 8 + Lost 16). All 72 are in the corpus as curated
transcripts, verified 2026-11-09, including three closed in v0.35.0:
`story-awaken-queensguard`, `story-we-stand-unbroken`, `story-retribution`.
BL-era storybooks, records and catalogue-side entries are present. The visible
Beyond Light gap is caption-tier (`source_tier='game_caption'`) provenance and
speaker labelling.

## Known gaps

| Gap | Recorded state |
|---|---|
| BL→LF subtitle/VO tier | Caption provenance exists only for builds actually ingested; no pre-BL VO tier is claimed. |
| BL→LF speaker-name labels | Name display is build-supplied where present. The older client does not carry it; unknown VO stays `Cutscene`. |
| Entity web for the BL era | `entity_links` extend beyond `beyond-light`; no pathological holes are recorded. |

## What shipped

- v0.37.0: schema 1.8.0; `sr_globals` name tables added to `Builds.md` and the
  entity web.
- v0.38.0: live-build lane.
- v0.39.0: schema 1.9.0; caption sighting log.

## Scope notes

- Re-translation of BL-era web captures is out of scope: they are already corpus
  canon, and drift is logged rather than rewritten.
- Re-extraction of 2019 / pre-BL material is out of scope; it stays as recorded.
- Packages the live client does not permit are not opened.
- v500/AES keys are not coded for this environment.
