# Work Queue

Prioritized maintenance queue after v0.38.0. Each item is written to be
executable without re-deriving context. Status values: `queued`, `active`,
`blocked`, `done`.

| # | Item | Priority | Estimate | Status |
|---|---|---|---|---|
| Q1 | Second-provenance table (`caption_sightings`) | P0 | 2–3 h | **done** |
| Q6 | Ecosystem pass: agents, template, tooling, tests, site | P0 | 4–6 h | **done** |
| Q2 | Parser for class `0x808099ef` | P1 | 3–6 h | queued |
| Q3 | Live-build refresh automation | P2 | 4–6 h | queued |
| Q4 | Caption-tier label in `character(all_lines=True)` | P3 | 30 min | **done** (Q6) |
| Q5 | Confirm `w64_sr_globals_0134` is empty | P4 | 30 min | **done** (Q6) |

---

## Q1 — Second-provenance table

**Status: done in v0.39.0 (schema 1.9.0).**

**Problem.** `caption_provenance` is one row per line (`line_id` PRIMARY KEY).
When a later build repeats text the corpus already holds, its sighting was
dropped (1,651 live lines onto 2020 canon, 3,572 cross-package repeats).

**Implemented.** `caption_provenance` stays the one-row-per-line current index.
`caption_sightings` is the observation log:

```sql
CREATE TABLE caption_sightings (
    line_id INTEGER NOT NULL REFERENCES transcript_lines(id) ON DELETE CASCADE,
    source_build TEXT NOT NULL REFERENCES builds(build_id),
    source_slug TEXT NOT NULL,    -- caption record slug
    line_ord INTEGER NOT NULL,    -- index in the record's lines array
    source_pkg TEXT, source_entry INTEGER, bank_entry INTEGER,
    record_index INTEGER, record_part INTEGER,
    kind TEXT, hash INTEGER,
    captured_at TEXT NOT NULL,
    PRIMARY KEY (line_id, source_build, source_slug, line_ord)
) WITHOUT ROWID;
```

Identity is the processed record line, not the physical slot: sunrise lines
carry no record index, and a slot key collapsed 1,070 genuinely distinct lines
(sharing a bank entry) in the first draft. `load_captions()` writes one
sighting for every non-empty record line, merged or new, and
`combine-live-captions.py` now retains cross-package repeats by default.

**Result.** 63,359 sightings (51,735 live + 11,624 sunrise), 7,681 merged
lines, 0 collapsed; `caption_provenance` unchanged at 56,119. The `sightings()`
gate derives expected totals from the JSONL, so it catches a key regression
without hardcoded counts.

**Acceptance met.** Every provenance row has a matching sighting; every
sighting resolves to a line and a registered build; expected per-record and
per-build totals come from the source; lines seen by both builds equal the
JSONL text intersection (1,651); no NULL `captured_at`; full rebuild and gates
green.

---

## Q6 — Ecosystem pass

**Prompt:** `/opt/vault/d2-bl-extract/COMPREHENSIVE-PASS-PROMPT.md`
**Report:** `/opt/vault/d2-bl-extract/reports/ecosystem-pass.md`

Bring every consumer of the v0.39.0 database in line: six agents, template and
persona generation, MCP/API/query tooling, tests, docs/wiki and the public site.
Seed defects: stale site counts and install sizes, `source-persona.py` resolving
caption-only speakers from `v_speakers`, missing schema-1.9.0 entry in
`GRIMOIRE-CHANGES.md`, and site roster data duplicated from the series registry.

Parallel plan: one read-only inventory + three read-only audits (agents, site,
template), then disjoint-repo edits, then a serial gate/deploy wave. Q4 and Q5
are closed inside this pass. Q2/Q3 remain separate and change the DB, so freeze
v0.39.0 or land them first.

**Result (v0.39.1):** Q4/Q5 closed; six agent audits green and docs synced;
template resolver fixed with a caption-only regression test; site counts now
come from `_data/grimoire.json` and deploy checks pass; `tests/docs-consistency.py`
is green. Q2/Q3 remain queued.

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
