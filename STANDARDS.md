# Standards (index)

> **Depends On:** none (standards reference)
> **Token Estimate:** ~0.8K tokens

The contract every file, script, and database row in this repository must meet.
The full standard lives in [`docs/process/Standards-Reference.md`](docs/process/Standards-Reference.md);
this file is the short index and change checklist. Verification gates (section 7 of the
reference) enforce these rules; a change that breaks them is a change that is not done.

## Quick links

- Scope and agnostic contract: `docs/process/Standards-Reference.md` (sections 1-2)
- Database contract and naming: `docs/process/Standards-Reference.md` (sections 3-5)
- Quoting policy: `docs/process/Standards-Reference.md` (section 6)
- Persona canon: `docs/process/Standards-Reference.md` (section 3, "Persona canon")
- Verification gates: `docs/process/Standards-Reference.md` (section 7)
- Agent interface contract: `docs/process/Standards-Reference.md` (section 8)
- Agent workspace contract: `docs/process/Standards-Reference.md` (section 9)
- Change procedure: `docs/process/Standards-Reference.md` (section 10)
- Packaging and platform portability: `docs/process/Standards-Reference.md` (sections 11-11a)
- README contract: `docs/process/Standards-Reference.md` (section 12)
- Agent document contract: `docs/process/Standards-Reference.md` (section 13)
- Release notes: `docs/process/Standards-Reference.md` (section 14)
- Licensing: `docs/process/Standards-Reference.md` (section 15)
- Agent engineering standards: `docs/process/Standards-Reference.md` (section 16)

## Required gates (must stay enforceable)

- Quote verification: `tests/test-db.sh`, `db/query.py verify`, `tests/caption-test.py`
- Canon policy: source hierarchy and provenance rules in the reference (section 1 (agnostic/corpus scope) / 3)
- Persona freshness: `tests/persona-freshness.py`, `tests/count-consistency.py`
- Voice consistency: per-agent voice suites (`tests/voice-scorer.py`, `tests/quote-verify.sh`)
- Cross-agent isolation: `tests/permission-leak-audit.py` (peer read/glob/grep denial)
- Agnostic contract: `tests/agnostic-test.py`, `tests/conformance.py`
- Finalize refusal conditions: `destiny-agent-template/finalize-persona.py --check`

## Change checklist

1. Ingest into `source/` (vault-local corpora stay local).
2. Rebuild: `python3 db/migrate.py`, `python3 scripts/apply-queen-fold.py`,
   enrichment steps, `python3 db/build_entity_web.py --db db/grimoire.db`.
3. Refresh derived docs: `python3 tests/sync-doc-counts.py`,
   `python3 tests/sync-readme-meta.py`, `python3 scripts/gap-report.py`,
   `bash scripts/sync-wiki.sh`.
4. Run gates: `bash grimoire-master-audit.sh` and per-agent `bash tests/master-audit.sh`,
   plus a fresh-clone spot check for layout changes.
5. Commit; push tags/releases as needed.

Database counts and suite totals are generated, not hand-maintained:
`tests/sync-doc-counts.py --check` and `tests/gen-suite-counts.py --check`.
Historical release notes are exempt from count sync.

## Repository layout

```
db/          # query.py, schema.sql, migrate.py, taxonomy.py, capabilities.json
source/      # ingested markdown: books, cards, transcripts, records
compendium/  # character quote index
archive/     # local-only extraction inputs
scripts/     # ingestion helpers
tests/       # archive gates, agent suites, shared runner, conformance
docs/        # wiki, taxonomy, discovery, process notes, standards reference
skills/      # agent-facing SKILL.md
series/      # registry of grimoire-born agents
mcp-server/  # optional MCP adapter
STANDARDS.md # this index
```
