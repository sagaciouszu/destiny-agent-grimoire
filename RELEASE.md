# v0.32.0 - Entity attribution folds (Osiris apparitions, Exo Stranger)

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.6K tokens

**2026-11-09**

Data-only release. No schema change (still 1.5.0). grimoire.db is the v0.31.0
database with the remaining owner-approved speaker folds applied.

## What's Changed

- **`Reflection of Osiris` → `Osiris`** (16 lines). The Taken-apparition
  qualifier rows are the same entity per owner ruling.
- **`Elsie Bray` + `Elisabeth Bray` → `Exo Stranger`** (10 lines). Exo Stranger
  IS Elsie Bray per Beyond Light; the two name-variant rows now ride with the
  entity. `Exo Stranger` and `Elsie Bray` both resolve to the same entity; the
  entity web will carry the independent aliases.
  Corpus total: 78,740 lines (unchanged). v_speakers 235 -> 233.
- **`db/migrate.py`** carries the same folds (`SPEAKER_ALIASES`) so a fresh
  rebuild reproduces this state.

## Gates

- `tests/test-db.sh` 61/61; `tests/lore-integrity.sh` 17/17.
- Coverage diff: none; sync-doc-counts in sync.
