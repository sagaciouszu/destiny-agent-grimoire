# v0.23.0 - Class-tagged canon and user preferences

**2026-11-04**

## What's Changed

- **Class tags:** Hunter, Titan and Warlock variants are tagged on transcript
  lines; `--class` returns base lines plus the chosen class.
- **Menagerie precision:** class callouts are optional; Calus has 419 base lines
  and 12 class variants.
- **User preferences:** per-user `memory.py prefs-set --class` stores the player's
  class locally; the shared canon never holds user data.
- **Onboarding:** agents ask for the class once, persist it, and pass it to
  `character`, `transcript` and `search`.
- **Schema 1.3.0**, query interface 89 checks.

## Verification

9/9 archive, 89/89 interface, 51/51 database, 15/15 generated Agent, 20/20 Drifter, 15/15 Eris, 15/15 Calus, 8/8 MCP, 141-call matrix, 10/10 extended, conformance PASS.

## Asset

`grimoire.db` with class tags, lore, taxonomy and verification indexes.
