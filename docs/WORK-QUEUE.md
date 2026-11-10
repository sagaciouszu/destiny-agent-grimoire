# Work Queue

Prioritized maintenance queue after v0.38.0. Each item is written to be
executable without re-deriving context. Status values: `queued`, `active`,
`blocked`, `done`.

| # | Item | Priority | Estimate | Status |
|---|---|---|---|---|
| Q1 | Second-provenance table (`caption_sightings`) | P0 | 2–3 h | **done** |
| Q6 | Ecosystem pass: agents, template, tooling, tests, site | P0 | 4–6 h | **done** |
| Q2 | Parser for class `0x808099ef` | P1 | 1 h spike | **done** (not prose) |
| Q3 | Live-build refresh automation | P2 | 4–6 h | **done** (v0.39.2) |
| Q4 | Caption-tier label in `character(all_lines=True)` | P3 | 30 min | **done** (Q6) |
| Q5 | Confirm `w64_sr_globals_0134` is empty | P4 | 30 min | **done** (Q6) |
| Q7 | Deep ecosystem pass: standards, template, agents/webs, recount, MCP, site | P0 | 6–8 h | **done** |
| Q8 | Tier filters, `v_canon_speakers`, access-test consolidation, refresh runbook | P0 | 4–5 h | planned |

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
are closed inside this pass. Q2 closed as non-prose; Q3 remains separate and
changes the DB, so freeze v0.39.0 or land it first.

**Result (v0.39.1):** Q4/Q5 closed; six agent audits green and docs synced;
template resolver fixed with a caption-only regression test; site counts now
come from `_data/grimoire.json` and deploy checks pass; `tests/docs-consistency.py`
is green. Q2 closed as non-prose; Q3 remains queued.

---

## Q2 — Class `0x808099ef`: closed, not prose

**Status:** done (2026-11-10) · **Verdict:** hash/reference table, no parser.

### Evidence

- 8,656 `*_808099ef_*.bin` files across 13 mounted packages; sizes 120–2,460 B.
- `0294/5892` is 152 B: header `0x50`, count 10, type `0x80800070`, followed by
  ten 32-bit values — not records and not UTF-8.
- The base `0x808099f1` entry at `0294/5892` held 38 text records (holiday
  cookie text). None of that text appears in the ef file.
- Across all 8,656 ef files: zero runs of three or more space-separated ASCII
  words, zero English markers.
- The patch replaces the text table with a hash/reference table; the prose is
  not carried in this class.

**Consequence.** No parser. `0294/5892` remains in the extractor's
`unparseable_entries` and the gap is recorded in
`archive/data/locale-maps/class-808099ef.skip.json`. Coverage is not loosened
to hide it.

---

## Q3 — Live-build refresh automation

**Status:** done (2026-11-10) · **Tooling release:** v0.39.2.

`scripts/refresh-live-build.py` automates the sequence: source validation,
layer unpack/merge, locale resolution, extraction (build-scoped slugs),
language validation, combine, drift report, build registration, rebuild and
gates. `archive/data/builds.json` is now the data-driven build registry, and
`db/migrate.py` loads `archive/data/live-builds/*.jsonl` alongside the current
captions file.

Acceptance met:
- current build is a no-op and exits 0;
- `--dry-run` plans every stage and writes nothing;
- `--self-test` proves a changed line appears in the drift report;
- a registered build is added to `builds.json` and survives a from-source
  rebuild;
- new build files use build-scoped slugs, so earlier builds are never rewritten.

A real second live build was not available in this environment; the synthetic
drift self-test and the current-build no-op are the exercised paths.

**Hardening after review:** failed gates roll back `builds.json` and the tier
file; drift compares against the latest registered build; validator output is
required (no silent partial tier); `--force` is refused on the current build;
`destiny2.exe` sha256 is checked/recorded; post-rebuild site/doc counts and the
docs-consistency gate run; punctuation-only drift is reported.

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
- Q2 → closed 2026-11-10 as non-prose (no parser, no DB change).
- Q3 → tooling release, no schema change.
- Q4/Q5 → batch into the next release; no DB artifact change for Q4.

---

## Q7 — Deep ecosystem pass

**Plan:** `/opt/vault/d2-bl-extract/DEEP-ECOSYSTEM-PLAN.md`

Ordered pass over the agnostic contract, template/generation, agent access and
knowledge webs, a full code recount with three scratch test agents (Ghost,
Drifter, Eris), MCP/skill/card decision, then stats/readmes/site. Designed for
a ~200k token envelope with a hard checkpoint before the 01:00 UTC DeepSeek
peak window.

**Gate:** P0 standards must land before any template/agent/site docs. Test
agents are scratch-only and are never published.

**P0 status (2026-11-10):** complete. `STANDARDS.md` carries the agnostic
contract and generated-artifact rules; shared doc/gate scripts read
`series/agents.json`; `tests/agnostic-test.py` enforces it in the master audit
(16/16; docs-consistency is in the same run); query-interface count corrected to 91. Census:
`/opt/vault/d2-bl-extract/reports/deep-census.{json,md}`. Next: P1 template
harness (including moving the legacy per-persona count patterns out of the
shared doc-sync script).

**P1 status (2026-11-10):** complete. The template ships a deterministic
fixture database (`tests/fixture-db.py`) and an offline generate/source test
(`tests/test-fixture-sourcing.py`); `tests/test-template.py` discovers its
optional real-corpus speaker from the data instead of naming one. `new-agent.py`
stages and promotes atomically, `finalize-persona.py` rejects zero canon, a
stale schema and caption-counted personas, and `setup.sh` gains `--dry-run`,
`GRIMOIRE_DB` and dangling-link recovery. `source-persona.py` stamps
`grimoire_schema`. Verification: template self-test (offline and real corpus),
caption resolver, fixture sourcing, token estimates, conformance and
docs-consistency. Next: P2 agent access and knowledge webs.

**P2 status (2026-11-10):** complete. All six agents share the template setup
contract (`--dry-run`, `GRIMOIRE_DB`, dangling-link recovery).
`tests/agent-access-test.py` proves setup help and dry-run behavior,
missing-database failure, read-only database access and site roster parity.
`scripts/generate-knowledge-web.py` owns a generated canon snapshot in every
agent `reference/knowledge-web.md` and runs `--check` in the master audit. All
six agent audits pass (20/20; Drifter 25/25); master audit 18/18. Next: P3
recount and scratch test agents.

**P3 status (2026-11-10):** complete. Recount at
`/opt/vault/d2-bl-extract/reports/deep-recount.{json,md}`; 16 duplicate code
groups are intentional shared helpers; no dead script confirmed. Ghost (2,690),
Drifter (1,149) and Eris (1,011) scratch agents all pass 20/20; stress cases
(caption-only, missing DB, old schema, sparse 20-line speaker, side-by-side)
pass. Scratch agents stay in `/tmp/opencode/test-agents/` and are not published.

**P4 status (2026-11-10):** complete. MCP contract 12/12, optimization 25/25,
matrix 8/8 (161 calls), probe 22 tools. `stats` now reports `missing_tables`
on a pre-1.9 database instead of failing; MCP README and skill document the
schema, caption-tier and `v_speakers` caveats. Card decision: defer
(`/opt/vault/d2-bl-extract/reports/card-decision.md`). Next: P5 stats, readmes
and site.


**P5 status (2026-11-10):** complete. Site stats regenerated for v0.39.3;
`scripts/sync-agents.py` now owns roster metadata (repo, entry, version, release
URL, last update, audit totals) and runs `--check` in `npm run check`; setup
pages document `--dry-run` and `GRIMOIRE_DB`. `npm run check` is green, the site
deployed (`9246e3d`) and live pages were spot-checked (9,229 transcripts, 22
tools, 25/25 and 20/20 audits). GitHub description updated; wiki in sync. Next:
P6 integration and release.

**P6 status (2026-11-10):** complete. Database is byte-identical to v0.39.3;
grimoire v0.39.4 released with `grimoire.db`, `.xz`, `.gz` and `SHA256SUMS`.
Six agents tagged and released (v0.1.6; Drifter and Eris v0.14.3). Site deployed
(`b6063e7`) and live pages spot-checked (Drifter v0.14.3 25/25, Zavala v0.1.6
20/20). Wiki in sync; all repositories clean. Final gates: master 18/18, six
agent audits 20/20 (Drifter 25/25), MCP 12/12, 25/25, matrix 8/8, template
offline and real-corpus, site `npm run check`, docs-consistency 5/5.


**Post-release cleanup (2026-11-10):** the last shared persona-specific count
patterns moved into `tests/doc-count-patterns.json` in the Drifter and Eris
repos. `tests/sync-doc-counts.py` now contains no persona name or repository.
Drifter 25/25 and Eris 20/20 remain green; conformance and docs-consistency
pass. This is on master after the v0.39.4 tag and will ride the next release.


## Q8 — Remaining work plan

**Plan:** `/opt/vault/d2-bl-extract/REMAINING-WORK-PLAN.md`

Order: explicit `--tier`/`--exclude-tier` filters, then `v_canon_speakers`
(schema 1.10.0), then consolidate the access gates, then the live-build refresh
runbook when a public build appears. Items A-C bundle into v0.40.0; item D is
trigger-based.

**Gate:** full rebuild and 18-suite audit for the schema view; agent audits for
the bundled release.
