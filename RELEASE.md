# v0.33.1 - The Queen split (Riven / Mara Sov)

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.6K tokens

**2026-11-09**

Data-only release. No schema change (still 1.6.0). grimoire.db is the v0.33.0
database with the 37 'The Queen' rows split by speaker per owner ruling.

## What's Changed

- **The Queen dissolved into two speakers by hand, line by line:**
  - `Riven` (22): all of `Nothing Left to Say` and `High Plains Blues`, every Forsaken-Season-4 cutscene line, the `Game caption (dialogue)` row, `The Machinist seq 8` ("Move.").
  - `Mara Sov` (15): all `Queen's Court` loops (1-7), `The Machinist seq 4/6` ("Be brave." / "Now take it.").
- Transcript lines total stays 78,740. v_speakers 233 -> 232.
- Method: 37 raw line ids retargeted in transcript_lines; transcript-sourced
  FTS rows (both `transcript_line` and `caption`) and verify_fts rows were
  dropped and rebuilt from live data in the same transaction to guarantee
  exact speaker/norm pairing. FTS count unchanged (130,210). No source
  files were edited.
- Rollback: this build is the canonical for the split; a from-source rebuild
  would reintroduce `The Queen` (expected, same class of caveat as earlier
  in-place normalizations, documented).

## Gates

- `tests/test-db.sh` 61/61 · `tests/lore-integrity.sh` 17/17 · query-interface 89/89
- verify --speaker "Riven"/"Mara Sov"/"The Queen" spot checks behave as expected
