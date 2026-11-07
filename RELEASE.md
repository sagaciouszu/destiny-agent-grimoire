# v0.29.1 - Documentation consolidation (caption provenance)

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.4K tokens

**2026-11-07**

Documentation-only release. No schema change; `grimoire.db` is byte-identical
to v0.29.0.

## What's Changed

- `docs/wiki/Captions.md` (new): the one caption explainer. Ingestion rules,
  provenance, the five verified speaker sources, exclusion, dedup, persona
  canon exclusion predicate, verification — cites `tests/caption-test.py` in
  place of definition.
- `docs/wiki/Database.md` updated to link it; `db/SCHEMA_VERSION` is the
  canonical schema file (consumed by `taxonomy.SCHEMA_VERSION`); `db/README.md`
  and `skills/destiny-grimoire/SKILL.md` reference `speaker_source` (schema 1.5.0).
- `STANDARDS.md` documents the caption contract: provenance mandatory, five
  verified sources only, NULL allowed only for `Cutscene`/`Narration`,
  captions never persona voice, FTS/verify mirror wording.
- `tests/docs-audit.py` gained a stale-token gate (rejects v0.28.0/1.4.0
  references; 378 commands checked).
- `tests/README.md` rewritten to the live catalog (14-suite audit, no stale
  specific numbers without asserts).
- `CHANGELOG.md` is now a pointer to GitHub releases; no hand-maintained body.

## Verification

Master audit 14/14; docs-audit 378 commands; conformance clean;
count-consistency 21/21; sync-doc-counts in sync.

## Asset

`grimoire.db` is byte-identical to v0.29.0; the `.xz`/`.gz` archives and
`SHA256SUMS` are carried forward by the release-assets workflow.
