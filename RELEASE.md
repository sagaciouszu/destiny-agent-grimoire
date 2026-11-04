# v0.26.0 - Reviewed activity dialogue and coverage status

**2026-11-04**

## What's Changed

- **Reviewed activity dialogue:** Ketchcrash (38 lines), PsiOps Battlegrounds
  (51), Defiant Battlegrounds (73) and Expedition (35), compiled from 63
  activity dialogue videos with speaker labels reviewed.
- **Honest coverage status:** the four remain `partial_transcript` because
  exhaustiveness is not provable. `coverage_notes` also records `no_dialogue`,
  `narration_only` and `dialogue_source_missing` with evidence.
- **Crow identity:** `The Crow` and `Crow` are one speaker, canonicalized to
  `Crow` (418 lines); a regression test enforces it.
- **Agent surface:** coverage status is returned by the API, CLI, MCP and
  activity detail. Agent persona counts are synced.
- **Gap ledger:** no activity is left in the generic “no transcript” bucket.

## Verification

9/9 archive suites, 89/89 query interface, 51/51 database, 16/16 taxonomy,
11/11 source cross-check, conformance PASS. Agent connections 36/36, parity
60/60. Exact-quote checks pass for Ketchcrash, PsiOps, Defiant and Expedition.

## Asset

`grimoire.db` with 1,312 transcripts, 68,776 canon lines and explicit coverage
notes for every remaining gap. SHA256 in `SHA256SUMS`.
