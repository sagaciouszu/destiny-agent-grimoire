# v0.33.2 - Nine-facet rename (Five -> The Nine)

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.4K tokens

**2026-11-09**

Data-only release. No schema change (still 1.6.0). grimoire.db is the v0.33.1
database with the remaining Nine-facet rows retargeted.

## What's Changed

- **`Five` → `The Nine`** (11 rows from Monument of Triumph — Character
  Dialogue). Owner ruling: Five is a Nine-facet ("Monument of Triumph" spoken
  by a primeval vessel named for a number); same for any other Nine-entry
  numeral labels that appear. Transcript lines total stays 78,740; v_speakers
  232 -> 231.
- **`db/migrate.py` SPEAKER_ALIASES** carries `Five -> The Nine` so a from-
  source rebuild reproduces the fold.
- Rollback: in-place retarget; pre-swap backup at backups/grimoire-pre-
  five-fold-2026-11-09.db.

## Gates

- `tests/test-db.sh` 61/61 · sync-doc-counts in sync · integrity_check ok
