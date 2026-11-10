# Work Queue

Prioritized maintenance queue after v0.38.0. Each item is written to be
executable without re-deriving context. Status values: `queued`, `active`,
`blocked`, `done`.

| # | Item | Priority | Estimate | Status |
|---|---|---|---|---|
| Q1 | Second-provenance table (`caption_sightings`) | P0 | 2–3 h | queued |
| Q2 | Parser for class `0x808099ef` | P1 | 3–6 h | queued |
| Q3 | Live-build refresh automation | P2 | 4–6 h | queued |
| Q4 | Caption-tier label in `character(all_lines=True)` | P3 | 30 min | queued |
| Q5 | Confirm `w64_sr_globals_0134` is empty | P4 | 30 min | queued |

---

## Q1 — Second-provenance table

**Problem.** `caption_provenance` is one row per line (`line_id` PRIMARY KEY).
When the live build repeats text the corpus already holds, the live sighting is
dropped: 1,651 emitted live lines merged this way, 116 onto non-caption
web/cutscene lines. The audit can list them only from the pre-load JSONL.

**Design.** Keep `caption_provenance` as the fast one-row-per-line index. Add:

```sql
CREATE TABLE caption_sightings (
    id INTEGER PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES transcript_lines(id) ON DELETE CASCADE,
    source_build TEXT NOT NULL,
    source_pkg TEXT,
    source_entry INTEGER,
    bank_entry INTEGER,
    record_index INTEGER,
    record_part INTEGER,
    kind TEXT,
    hash INTEGER,
    captured_at TEXT,
    UNIQUE (line_id, source_build, source_pkg, bank_entry, record_index, record_part)
);
```

- `migrate.py` writes a sighting for **every** caption line, including merged
  ones, and backfills one sunrise sighting per existing provenance row.
- `caption_provenance` remains the canonical/current row; `caption_sightings`
  is the observation log.
- Schema bump to 1.9.0; `db/capabilities.json`, `db/README.md`, `Database.md`.

**Acceptance.**
- Every caption line has ≥1 sighting; no duplicate
  `(line, build, package, entry, record, part)`.
- The 1,651 merged live lines have exactly 2 sightings (era + live).
- `tests/caption-test.py` gains `sightings()` covering both invariants.
- Full rebuild + all gates green; release v0.39.0.

**Risks.** New table increases DB size slightly; keep `caption_provenance`
unchanged for query speed. Do not make the API join the sightings table by
default.

---

## Q2 — Parser for class `0x808099ef`

**Problem.** Patch layers replace 13 entries per affected table with class
`0x808099ef` (header size `0x50`, not `0x40`). `0294/5892` is one such English
entry; the extractor skips it and logs `unparseable_entries`. Across the 15
packages, 636 entries are class replacements, so the gap is larger than one
line.

**Investigation.**
1. Dump `5892_808099ef_t8_s0.bin` and its sibling locales; compare record
   layout with the `0x808099f1` parser in `scripts/extract-live-captions.py`.
2. The header has `0x50`, an array of `0x80d41a12`-style hashes at `0x18`, and
   `0x80809fb8` near `0x5c`. Determine whether it is a StringBank variant
   (hash-keyed records) or a wrapper around another class.
3. Decode one record and compare against the English text the table would
   carry (neighbouring locales / item corpus).

**Acceptance.**
- A `parse_ef` implementation with structural asserts and a fixture test.
- `0294/5892` yields English text; the language gate and independent English
  check both pass for it.
- Every class-replaced entry is either parsed or skipped with a reason in the
  stats sidecar; no silent gaps.
- Re-extract affected packages only; regenerate maps/stats; rebuild + gates.

**Risks.** The class may not contain prose at all (could be a hash table or a
different bank type). If so, close Q2 as "not prose" and record the evidence;
do not force a parser.

---

## Q3 — Live-build refresh automation

**Problem.** Widening was run by hand: copy build, extract 36 layers, merge,
resolve, extract, validate, combine, rebuild. A live update will need the same
sequence, and manual runs are where provenance mistakes happen.

**Design.** `scripts/refresh-live-build.sh` (or `.py`) with `--dry-run`:

1. Read the installed build id (`steamcmd` app_info or the build stamp) and
   compare with `builds`.
2. Copy a new build to `/opt/vault/d2-bl-extract/build-<id>/`; verify
   `destiny2.exe` hash and file count.
3. Unpack every `w64_sr_globals_*` layer; `merge-pkg-layers.py` per family.
4. `resolve-locales.py` per family; diff the new map against the committed one
   and report added/removed entries.
5. `extract-live-captions.py` with the committed maps; validate language;
   `combine-live-captions.py`; write the combined report.
6. Rebuild, gates, and a drift report: per package, lines added/removed/
   rewritten, speakers changed, entries newly empty.
7. Never rewrite an era capture; a changed line is a new sighting (Q1), not an
   inline edit.

**Acceptance.**
- Running against the current build is a no-op (0 changed lines) and exits 0.
- `--dry-run` prints every step and writes nothing.
- A synthetic one-line patch produces a drift report naming that line.
- `builds` row updated with `captured_at` and extraction notes.

**Risks.** SteamCMD branch access is public-only; a build that is not on the
public branch cannot be fetched. Record `unavailable` rather than substituting
an older build.

---

## Q4 — Caption-tier label in `character(all_lines=True)`

**Problem.** `character(all_lines=True)` returns caption rows for speakers
without a curated `character_lines` entry under a "transcript lines" header.
The rows are legitimate searchable canon, but the header does not name the
tier, and `character_info.spoken_lines` deliberately excludes captions.

**Fix.** Select `t.source_tier` and either:
- label the header `=== <name> (transcript + caption lines) ===`, or
- add `--tier` filtering (`canon|all`) defaulting to current behaviour.

**Acceptance.** Query-interface tests cover both; persona counts unchanged.

---

## Q5 — Confirm `w64_sr_globals_0134` is empty

`resolve-locales.py` reports 0 English entries and 0/0 tables for `0134`.
Confirm the package is:
- a different class family (not StringBank), or
- genuinely empty in this build.

Write the answer into `docs/wiki/Builds.md` (one sentence) and the stats
sidecar. Do not treat it as covered.

---

## Release cadence

- Q1 → v0.39.0 (schema 1.9.0).
- Q2 → v0.39.x or v0.40.0 depending on whether it adds entries.
- Q3 → tooling release, no schema change.
- Q4/Q5 → batch into the next release; no DB artifact change for Q4.
