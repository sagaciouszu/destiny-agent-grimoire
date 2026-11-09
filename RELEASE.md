# v0.30.0 - D1 speaker attribution normalization

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.5K tokens

**2026-11-09**

Data-only release. No schema change (still 1.5.0). `grimoire.db` is the
v0.29.1 database with speaker attribution normalized for the Destiny 1
family; nothing else moved.

## What's Changed

- **D1 speaker labels normalized** in `transcript_lines`, `fts.speaker` and
  `verify_fts.speaker` (one transaction, the three-table sync the caption
  pipeline uses). Exactly three mappings, scoped to transcripts classified
  to `destiny-1`, `the-dark-below`, `house-of-wolves`, `the-taken-king` and
  `rise-of-iron` (123 transcripts, 4,140 lines), and nothing else:

  | raw label | canonical | rows |
  |---|---|---|
  | `GHOST` | `Ghost` | 11 |
  | `MASTER RAHOOL` | `Master Rahool` | 1 |
  | `Saladin` | `Lord Saladin` | 59 |

  `transcript_lines` total unchanged at 78,740; zero rows changed speaker
  without one of these mappings; FTS and the verification index carry the
  same renaming, so `verify --speaker "Lord Saladin"` resolves D1 Iron
  Banner dialogue and `--speaker Saladin` correctly returns nothing.
- **Honest scope statement:** normalization only. No new transcripts, no new
  lines, no coverage change (coverage report byte-identical before/after:
  78,740 rows / 71,969 dialogue lines / 71 catalogued activities /
  9 rotating events), personas unchanged, `source_tier=ishtar_web`
  provenance kept, `speaker_source` untouched.
- **Kept as-is, unmapped (observed, not errors):** 26 `GHOST` rows outside
  the D1 family (other expansions, outside the approved scope); legacy and
  generic labels such as `Guardian` / `The Guardian`, `Speaker` /
  `The Speaker`, `Narration`, `Cutscene`, `Unknown`, `Archive`, `Relic`,
  `Knight`, `Awoken Guard`, `Tevis`, `Lodi`, `Skola`, `Ouros`,
  `Echo of Oryx`, `Praedyth`, `Toland`, `Lakshmi-2`, `Tyra`, `Saint-14`
  and the existing short forms (`Ikora`, `Zavala`, `Petra Venj`,
  `Master Rahool`).
- **Rebuild caveat:** the normalization is applied to the shipped database;
  `SPEAKER_ALIASES` in `db/migrate.py` was deliberately not extended (it is
  global and would also rename the 26 non-D1 `GHOST` rows on rebuild), so a
  full rebuild from source currently reintroduces the raw D1 labels. The
  attached `grimoire.db` is the normalized artifact. Extending alias coverage
  is flagged to the maintainer as a follow-up decision.
- Docs count sync: `README.md` `v_speakers` 267 -> 265, `verify_fts`
  unchanged, total rows 551,461 -> 551,459.

## Verification

test-db 61/61 (integrity ok; v_speakers 265; meta counts match live
tables); lore-integrity 17/17; coverage-report byte-identical before/after;
sync-doc-counts in sync; integrity_check ok; speaker histogram diff for the
123 D1 transcripts shows exactly the three mappings above and nothing else.

## Asset

`grimoire.db` is the v0.29.1 database with the three-table speaker sync
above; `SHA256SUMS` attached. Companions `grimoire.db.xz` / `grimoire.db.gz`
and refreshed `SHA256SUMS` are attached by the release-assets workflow on
publish. Rebuild reference (does not reproduce the normalization; see the
rebuild caveat): `python3 db/migrate.py` plus the enrichment steps in
`docs/wiki/Testing-and-Auditing.md`.
