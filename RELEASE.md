# v0.33.0 - Entity web (schema 1.6.0); Elsie Bray is now the canonical label

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~1.8K tokens

**2026-11-09**

Schema goes **1.5.0 → 1.6.0**. One new additive layer: the entity web
(4 tables plus 1 relations table plus build meta, 3 public views, 88 named
entities, 134 aliases, 24,196 entity-to-document links). No existing
table, column or view is touched; books, lore entries and transcript prose
are read-only build input, proved byte-identical below. v0.32.0 tag is
left alone; this release also carries the Elsie Bray speaker canonicalization
(the flip) that the owner landed today.

## Books and cards SHA256 proof

`source/books` + `source/cards` hashed before the build, after the build,
and after the swap (2999 files, `LC_ALL=C sort -z` order):

```
$ ( find source/books source/cards -type f -print0 | LC_ALL=C sort -z \
      | xargs -0 sha256sum ) > tN.sha256   # T0 (pre-build) == T1 == T2
$ diff t0.sha256 t1.sha256 && echo BOOKS+CARDS UNCHANGED
BOOKS+CARDS UNCHANGED
$ git status --porcelain -- source/books source/cards
(empty)
$ sha256sum source/books/*.md | sha256sum
41454c63b3029ce8df4da3f0af19933a0e180779d402592fecc3264a0738eea6  -
```

`sha256sum -c` on the baseline manifest prints zero non-OK lines. The
pre-swap DB (owner's flip applied, no entity web) is preserved locally as
`/tmp/opencode/grimoire.db.pre-swap-v0.33.0`.

## What's Changed

- **Entity web (new, additive).** `entities`, `entity_aliases`,
  `entity_links`, `entity_relations`, `entity_build_meta` + public views
  `v_entity_resolve`, `v_entity_documents`, `v_entity_coverage`. Books,
  lore and transcripts are never UPDATEd; extraction is a read-only scan.
  - 88 entities: 55 char, 8 power, 6 faction, 19 place.
  - 134 aliases; folded duplicates merged (GHOST→Ghost, Saint XIV and
    Saint-XIV→Saint-14, OSIRIS→Osiris, etc.).
  - 24,196 links (transcript 6,752 · item 9,818 · book 1,099 ·
    book_entry 2,585 · lore_entry 3,642 · record 295 · seal 5).
    By match class: attribution 2,257 · canonical 16,217 · alias 3,641 ·
    ctx_alias 2,081.
  - Zero unlinked entities. ≥5 documents for 98.2% of chars, ≥10 documents
    for 100% of places and 87.5% of powers (The Winnower 7, The Gardener 11,
    Siren of Riven 2 attribution-only; see known limits).
  - Context rule: `the tower`, `tower`, `mercury`, `Diner`, `Pulled Pork`,
    `gardener`, `the gardener`, `winnower` match only attribution slots or
    the first sentence, so "the tower of banking" style prose never links.
    Weights: attribution 4.0, canonical 3.0, reviewed alias 1.5,
    ctx-satisfied 0.75, aggregate `max + 0.25 * (distinct aliases - 1)` cap 4.0.
- **The Elsie Bray flip rides this release.** The owner's canonicalization
  moved the corpus from `Exo Stranger` to `Elsie Bray` before this build
  (185 rows in `transcript_lines`, was `Exo Stranger`/`Elisabeth Bray`/
  `The Exo Stranger`; corpus total unchanged at 78,740). The entity web
  models `Elsie Bray` as the canonical entity name; `Exo Stranger`,
  `Elisabeth Bray` and `The Exo Stranger` are all aliases of it
  (beyond Light). `SPEAKER_ALIASES` in `db/migrate.py` carries the flip, so
  a fresh rebuild reproduces it; nothing was hand-edited in the built DB.
- **Public API:** three new views (above). CLI: `python3 db/query.py entity
  "<name>"` (aliases, document counts, top documents, relations, fuzzy-flagged
  candidates) plus `search --entity <name>`. MCP: new tool `entity(ref)`
  (22 tools now), `search` gains optional `entity:`, new resource
  `grimoire://entities` (~8.6 KB), tool map/instructions updated. `db/
  capabilities.json` synced; `db/README.md` and the wiki updated.
- **Schema 1.6.0** (`meta.version`, `SCHEMA_VERSION`); `meta.last_updated`
  2026-11-09; new live-count keys `entities`, `entity_aliases`,
  `entity_links`, `entity_relations`, `entity_build_meta`.
- Build mechanics: temp copy (`/tmp/opencode/grimoire-build.db`) → build →
  ref-integrity check (every ref resolves to exactly one parent row) →
  gates on the built bytes → books/cards SHA256 T1 → atomic rename into
  `db/grimoire.db` (fsync + rename in one directory) → gates re-run on the
  live file. Rollback: restore the pre-swap copy.

## Gates

- `tests/test-db.sh` 61/61 (schema 1.6.0 vs file; capabilities sync OK).
- `tests/lore-integrity.sh` 17/17.
- `tests/query-interface-test.sh` 89/89.
- `tests/mcp-test.py` 12/12 (22 tools registered).
- `tests/mcp-matrix-test.py` 8/8, 161 calls (entity round-trips included).
- `python3 tests/docs-audit.py` PASS (404 commands).
- `python3 tests/sync-doc-counts.py --check` in sync.
- FTS spot checks green: `hive` → 2,768 rows; verify_fts 130,210 = live
  count; `integrity_check` ok; no WAL sidecars (journal_mode=delete).
- Resolver latency p50 0.009 ms / p95 3.6 ms over 1,092 queries (exact
  folded match first, indexed). FTS top-10 p50 3.7 ms, p95 8.9 ms.

## Numbers (re-derived from the built DB)

| kind | entities | with links | links |
|---|---|---|---|
| char | 55 | 55 | 13,009 |
| faction | 6 | 6 | 1,712 |
| place | 19 | 19 | 6,814 |
| power | 8 | 8 | 2,661 |
| **total** | **88** | **88** | **24,196** |

Storage delta: 237,961,216 → 243,183,616 B = **+5,222,400 B (+2.2%)**,
vs the 15% (≈34 MB) budget. row `v_entity_documents` 24,196 rows.

## Owner rulings encoded (verbatim)

Every rule below is implemented as written; they are the build spec, not
commentary:

- Exo Stranger and Elsie Bray are one entity with independent aliases (both
  resolve to the same entity from the search surface).
- Reflection of Osiris is already folded into Osiris in the DB; the entity
  web treats them as the same entity.
- Siren of Riven is an entity adjacent to Riven (creation of her will);
  modelled with `entity_relations.adjacent_to`, not as an alias.
- Memory/Nightmare-of-X labels stay as transcript speaker labels; this
  release does not create entity rows for them (see limits). Personification
  voices (Vision of Light, Darkness, Light) keep their labels, adjacent
  relations, not merged.
- Glint is a distinct entity (Crow's Ghost); aliases Diner and Pulled Pork;
  char kind kept.
- Clovis Bray = Clovis Bray I = Clovis Bray AI is ONE entity
  (`clovis bray`, `clovis bray ai`, `clovis bray i` are its aliases).
- Rasputin is a separate entity (char) created by the Clovis Bray org; not
  merged with anything. The Great Machine (Eliksni/Fallen term) is The
  Traveler: aliases `great machine` and `the great machine` of the Traveler
  entity.
- Gardener = Traveler (Light primeval), Winnower = Darkness primeval: both
  are entities with `related_to` links (The Gardener → The Traveler,
  The Winnower → The Darkness); NOT aliases.
- Five is EXCLUDED from this build (owner watching the Monument of Triumph
  video first).
- Xol is kept as a power, per the proposal: The Worm entity carries `the
  worm`, `xol`, `worm god` (all reviewed=1 by owner ruling).
- SIVA: EXCLUDED this round (report only, still unbuilt).
- Taken, Scorn, House of Light, New Monarchy are not in the high-confidence
  set and were not added (no owner sign-off); they stay out.
- Only high-confidence lexicon rows were auto-linked; medium/low rows are
  not in the build (owner-commissioned exceptions are listed above).

## Known limitations (honest)

- Speaker labels `Memory of <base>` and `Nightmare of <base>` remain
  transcript speaker labels; no entity rows were created for them this
  release. When they are modeled, they will be entities with `adjacent_to`
  relations to the base entity (same for personification voices).
- Siren of Riven: one entity, 2 attribution links (last-wish, the-shattered-
  throne-dialogue). Honest yield, not padding.
- The Winnower: 7 documents, all `ctx_alias` (first-sentence context only).
  The Winnower/Gardener parable language is genuinely rare.
- Five excluded pending owner's Monument of Triumph review. SIVA excluded.
  Species (Cabal/Hive/Awoken/Vex/Eliksni/Scorn/Taken) are not entities;
  FTS handles species search.
- `Titan`/`Io`/`Neptune`-class place aliases that double as common words
  ship with `requires_ctx` or are absent by design; this build never links
  bare `moon`, `light`, `nine`, `saint` or `tower` mid-sentence.
- Items matched via `title + text`; 16,071 items with empty `norm_text`
  were still scanned (titles only); the 2 binary/encrypted lore entries
  (`Decompiled`, `Reconciliations`) folded to under 3 chars and were skipped
  by the scanner, as designed.
- No FTS retune in this release (FTS is untouched and still correct); the
  entity web is a separate additive surface.
- `Grimoire://entities` carries the full 88-entity index; it is ~8.6 KB of
  the 16 KB resource cap.

## Appendix: table and index list

| object | rows | indexes |
|---|---|---|
| entities | 88 | idx_entities_kind |
| entity_aliases | 134 | UNIQUE(alias), UNIQUE(norm_alias), idx_entity_aliases_entity |
| entity_links | 24,196 | UNIQUE(entity_id, kind, ref), idx_entity_links_entity, idx_entity_links_kind_ref, idx_entity_links_rank |
| entity_relations | 3 | UNIQUE(entity_id, relation, target_entity_id), idx_entity_relations_target |
| entity_build_meta | 14 | PRIMARY KEY(key) |
| v_entity_resolve | 134 | stored query |
| v_entity_documents | 24,196 | stored query |
| v_entity_coverage | 4 | stored query |

Ref grammar: slug tables (`transcripts`, `books`, `items`, `records`) → the
slug; row tables → `table:id`; hash-keyed tables → `table:hash`
(`lore_entries:<hash>`, `seals:<hash>`). Integrity of every ref was verified
at build time (zero dangling refs) and holds under `grimoire-master-audit.sh`.
