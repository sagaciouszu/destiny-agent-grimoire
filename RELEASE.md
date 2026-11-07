# v0.28.0 - Game caption corpus from the local build

**2026-11-06**

## What's Changed

Everything since v0.27.5:

- **English game captions join the canonical corpus.** 1,106 caption
  transcripts and 9,283 new lines load from `archive/data/captions.jsonl`
  (11,624 curated lines, committed) as `source_tier='game_caption'`,
  `lang='en'`, with per-line StringReference provenance in the new
  `caption_provenance` table (9,608 rows). A caption line whose normalized
  text already exists in canon is never inserted twice: its hash and package
  origin attach to the existing row instead (2,341 such lines), so search
  returns no duplicates and introduces no second attribution.

- **Curated facets, never guessed.** 37 activity facets (Crucible, Gambit,
  Menagerie, Trials of Osiris, Trials of the Nine) are stored as
  `confidence='derived'` from the reviewed extraction verdict with
  season/expansion filled from the activity catalogue; every other caption
  transcript stays honestly `unknown`. `taxonomy.CAPTION_ACTIVITY_SLUGS` maps
  extraction keys to taxonomy slugs, and vocabulary drift now fails the build
  log and `tests/caption-test.py`.

- **New search surface.** `--type captions` (fts and verification index
  `source='caption'`), a `lang` filter on `search()` / `search_total()` /
  the MCP `search` tool (`transcripts.lang`, `fts.lang`, every row `en`
  today), and caption rows reachable through `--activity`. Ranked search
  gives caption rows a -1.0 boost while stage-direction penalties still
  demote scoreboard rows (`speaker='Narration'`, `is_stage_dir=1`).

- **Persona canon excludes captions.** `persona.json` `canon_lines` keeps
  counting the corpus each persona was built from, so a caption drop never
  rewrites an agent persona. One predicate now runs in
  `tests/persona-freshness.py` (every agent repo),
  `tests/count-consistency.py`, `character_info.spoken_lines` and the agent
  template's persona generator.

- **Schema 1.4.0.** `transcripts.lang`, `fts.lang` (UNINDEXED),
  `caption_provenance`, the `db/capabilities.json` contract, the
  `Emperor Calus -> Calus` speaker alias and four PvP activity slugs
  (`crucible`, `gambit`, `trials-of-osiris`, `trials-of-the-nine`).

- **Gates.** New `tests/caption-test.py` (9 checks) wired into
  `grimoire-master-audit.sh` and CI against the smoke build;
  `tests/test-db.sh` and `tests/lore-integrity.sh` now select an FTS5-capable
  `sqlite3`, which turns five PATH-shadowed false failures into 61/61 and
  17/17.

## Verification

Master audit 14/14; extended suite 12/12 (robustness 26/26, MCP contract
12/12, MCP matrix 154 calls, MCP agent-optimization 25/25, checksum,
db-source-crosscheck 11/11, retrieval-eval P@5=0.96 / MRR=1.00, item audit,
docs audit 375 commands, taxonomy deep 17/17, agent connections and parity).
test-db 61/61; caption-test 9/9; query interface 89/89; lore integrity 17/17;
conformance 163 files clean; count-consistency 21/21; doc counts and README
metadata in sync.

## Asset

`grimoire.db` rebuilt from tracked sources plus local enrichment dumps;
companions `grimoire.db.xz` / `grimoire.db.gz` and refreshed `SHA256SUMS` are
attached by the release-assets workflow on publish.
