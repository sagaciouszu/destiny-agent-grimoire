# Beyond Light → Renegades — Ingestion Roadmap

**Status**: historical roadmap; the live-build lane shipped v0.38.0 and the
sighting log followed in v0.39.0 (schema 1.9.0).

## What the arena looks like (evidence-backed)

Builds referenced here: `sunrise-pre-bl` (2020) and `build-25932352`
(Update 9.7.0.6, Oct 2026), Steam appid 1085660, v53 container, AES-wrapped
everywhere. This page is historical and does not track the current live build.
Shelf-life note from
the private probe report (`build-25932352-probe.md`, not distributed):

- 2,417 `.pkg` on disk, matches Steam install byte-for-byte.
- `w64_sr_globals_0294_0` contains multi-locale tables of **names**: enemies
  (Nightmare / Scorn / Remnant tiers — file 21 has "Nightmare of Kra'lok"),
  feats & buffs (file 138, file 47), and placeholders. Files are one-per-
  locale per table-type:
  - `0_` = ES, `1_` = IT, `24_` = FR, `29_`/`60_`/`125_`/`151_`/… = EN sets.
  - Sample decoding, file `21_808099f1_t8_s0.bin`: EN nightmare-names table
    (crush the same list at `0_` = Spanish). Rows are concatenated as one
    text-table inside each file; byte offsets stable.
- `w64_sr_dialog_*_en_*.pkg` packages contain the *VO-side* descriptor data
  (`0x8080bca8`, ~8 k entries per package, paired to Wwise `t26/t6`). No
  English text is inside these files; NPCs' names are referenced by FNV-1
  hashes into `sr_globals`.
- `sr_globals` is shared across all 6 locales: extracting one header file
  yields 6 locales' name tables together; no need to also distribute patch
  containing `SR_GLOBALS_*`.

## Beyond Light coverage at v0.36.0

Beyond Light-era source entries on the Ishtar timeline: 72 (30 BL proper +
Hunt 5 + Chosen 13 + Splicer 8 + Lost 16). All 72 are in the corpus as
curated transcripts (verified 2026-11-09, incl. the 3 stragglers closed in
v0.35.0: `story-awaken-queensguard`, `story-we-stand-unbroken`,
`story-retribution`). BL-era storybooks, records and catalogue-side entries
are all present. **Beyond Light's missing work is exclusively caption-tier
(`source_tier='game_caption'`) provenance and speaker labelling.**

## What's missing and why it matters

| Gap | State |
|---|---|
| BL→LF subtitle/VO tier | Available only after the Phase 2 extraction plan |
| BL→LF speaker-name labels | 2024+ HUD-style name display exists per
gameVersion note; not present on the 2019 client (≤ Shadowkeep). Hard to split
by table; must detect/adapt the 2024 tables first. |
| Entity web gaps for BL era | `entity_links` beyond `beyond-light` present,
no pathological holes (BL ecosystem alive before BL launch extraction provenance). |

## Ingestion plan (two phases, with a hard gate)

### Phase 2a — `sr_globals` unlock (EN + target locales)

Attack vector: split-file strategy instead of one big flip.

1. Decode `w64_sr_globals_0294_0` files `621_`, `580_`, `151_`, etc. as EN
   enemy/ability tables; ally scoped names → BL ships-with-the-Voc vocab
   baseline.
2. Identify language rows by file prefix offsets (`1295_` = EN, `0_` = ES);
   rederive each locale; split into three promoted tables matching
   `english_name_tables.json` shape.
3. Wire `db/migrate.py` so VO extraction picks up localized name tables and
   propagates into FTS indexes; evaluate recall on 10 live canon lines.

**Deliverable:** `Builds.md` gains an EN-globals section; entity web
gains ~30 new links (enemy-title lookups only); release `v0.37.0` shipped
`schema 1.8.0`; `v0.39.0` shipped `schema 1.9.0`.

### Phase 2b — EN VO tier (Beyond Light only first)

Tight prove-of-extraction lane, stop before the full Beyond Light batch:

1. Detect the English-host narrative package(s) of Beyond Light
   (`w64_sr_dialog_v6xx_0205_en_*` and siblings); identify the emitter ref
   for monologue lines about Beyond Light (Chalcaist/Vanthas/Erien/Imperial).
2. Decode `t26/s6` / `HIRC` chunks to harvest actual line strings;
   ships Beyond Light VO.
3. Output to `archive/data/captions-post-bl.jsonl` with `source_build=
   'build-25932352'`; load to DB; run entity web + QFT sweeps; re-check
   counts; ship `v0.37.0` on the same tag.

### Phase 2c — Speaker HUD labels for BL tier

Gate after P2b lands: verify 2024 HUD name table integration to stamp
`speaker_source='hud-label'` instead of just `Cutscene` for in-world m8 lines
with `is_stage_dir=0`. Timed to v0.38.0.

## Decision rules

- Stop-loss 6 h per phase; go back to web captures for anything not perfectly
reconciled by that window.
- Phase 2a is enough to land v0.37.0; 2b/2c are sequenced but not blocking.
- Speakers must never ship as fact unless 2024 HUD prints them; BL below-light
  era ships `speaker='Cutscene'` on unknown VO just like `sunrise-pre-bl`.

## Something IS not true about what exists

The following items are out of scope for this plan:

- Re-translation of BL-era web captures. Already corpus canon; drift log only.
- Re-extraction of 2019 / pre-BL (it works and stays as-is).
- Force-opening packages the live client does not permit.
- Coding v500/AES keys for this environment.
