# v0.31.0 - D1/D2 speaker attribution normalization, round 2

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.8K tokens

**2026-11-09**

Data-only release. No schema change (still 1.5.0). `grimoire.db` is the
v0.30.0 database with the remaining speaker-label variants folded in one
transaction.

## What's Changed

- **30 additional label folds** into their canonical speakers, applied in a
  single atomic transaction across `transcript_lines.speaker`, `fts.speaker`
  and `verify_fts.speaker` (the three-table sync the caption pipeline uses).
  Transcript lines total stays 78,740; nothing else moved.

  | raw label | canonical | rows |
  |---|---|---|
  | Amanda | Amanda Holliday | 30 |
  | Holliday | Amanda Holliday | 130 |
  | Ana | Ana Bray | 24 |
  | Anastasia | Anastasia Bray | 1 |
  | Asher | Asher Mir | 95 |
  | Empress Caiatl | Caiatl | 5 |
  | Sjur Eido | Eido | 25 |
  | Devrim | Devrim Kay | 108 |
  | Eva | Eva Levante | 1 |
  | The Exo Stranger | Exo Stranger | 3 |
  | Elisabeth Bray | Elsie Bray | 6 |
  | Fikrul | Fikrul, the Fanatic | 15 |
  | The Fanatic | Fikrul, the Fanatic | 14 |
  | Emissary (Orin) | Emissary | 26 |
  | The Emissary | Emissary | 18 |
  | Orin | Emissary | 8 |
  | GHOST | Ghost | 26 |
  | Ixix, Apothecary | Ixis, Apothecary | 1 |
  | Queen Mars Sov | Mara Sov | 1 |
  | Sathona | Savathûn | 3 |
  | Xi Ro | Xivu Arath | 2 |
  | Shiro | Shiro-4 | 25 |
  | The Spider | Spider | 51 |
  | Nine | The Nine | 4 |
  | Tyra | Tyra Karn | 7 |
  | Tyra Karn's Voice | Tyra Karn | 1 |
  | The Witness | Witness | 10 |
  | Female voice | Unknown female voice | 1 |
  | Unidentified Female | Unknown female voice | 1 |
  | Zaval | Zavala | 1 |
  | Auryx | Oryx | 4 |

  Speaker coverage: v_speakers 265 -> 235.
- **Underlying rule keeping rebuilds sane:** `db/migrate.py` `SPEAKER_ALIASES`
  carries the same folds so a from-source rebuild reproduces the same
  canonical forms (v0.30.0's rebuild caveat is closed for these rows).
  `speaker_aliases` updated the same way (`HOLLIDAY` now targets `Amanda Holliday`).

## Not changed (owner decisions, kept)

- `Memory of …` / `Nightmare of …` rows stay as-is; the entity web will
  carry the adjacency relation (not folded).
- Clovis Bray vs Clovis Bray AI stand separately; `Rasputin` vs the Warmind
  stand separately; The Great Machine treated as Warmind-manifestation, not merged.
- Exo Stranger and Elsie Bray: only the named-fold rows landed; full 185-line
  Exo-Stranger/Elsie unification stands with the owner ruling for the combined
  entity's canonical.

## Gates

- `tests/test-db.sh`: 61/61. `tests/lore-integrity.sh`: 17/17.
- Coverage diff: none (same 2,422 transcripts / unchanged activity stats).
- `sync-doc-counts.py --check`: in sync; README v_speakers 265 → 235.
