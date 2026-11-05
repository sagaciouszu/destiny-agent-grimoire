# v0.27.2 - Dialogue expansion and contract corrections

**2026-11-05**

## What's Changed

Everything since v0.27.1:

- **Four partial activity transcripts expanded with 212 verified net-new
  dialogue lines** from 131 activity dialogue videos:
  - Ketchcrash: 38 -> **90** lines (32 sources)
  - PsiOps Battlegrounds: 51 -> **120** lines (35 sources)
  - Defiant Battlegrounds: 73 -> **120** lines (38 sources)
  - Expedition: 35 -> **79** lines (26 sources)
  - Total for the four: 197 -> **409** lines. Junk speakers and URLs were
    filtered, duplicates removed against the whole canon, and every file is
    still marked `partial_transcript` because exhaustiveness is unproven.
- **Wiki sync:** `scripts/sync-wiki.sh [--check|--push]` publishes `docs/wiki/`
  and refuses model-control tokens or content drift; the public GitHub wiki
  was republished clean (10 corrupted pages replaced, Home 69 -> 316 words).
- **OpenClaw onboarding:** `scripts/ensure-openclaw-mcp.sh` upserts an absolute
  MCP path into the OpenClaw config (idempotent, backs up first); wired into
  every `setup.sh` and the `--openclaw` sync. Doctor lint:
  `ok: true, findings: []`.
- **Persona counts synced** to the expanded canon: Drifter 1,149, Eris 1,011,
  Zavala 638.
- **STANDARDS corrections:** tier-aware provenance URLs (Destinypedia/Commons
  rows keep their real source), complete verification-gate list, release and
  README-metadata rules aligned with what conformance enforces, and approval
  nuance for standing grants.

## Verification

11/11 archive suites, 17/17 taxonomy, 89/89 query interface, 51/51 database, 354 documented commands + skills spec, MCP contract 10/10, agent connections 36/36, parity 60/60, conformance PASS. Exact-quote checks pass on all four expanded transcripts.

## Asset

`grimoire.db` with 1,314 transcripts, 69,217 canon lines and 20 speaker
aliases. SHA256 in `SHA256SUMS`.
