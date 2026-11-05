# v0.27.1 - Portability, safety and speaker identity

**2026-11-05**

## What's Changed

Everything since v0.27.0:

- **Saint-14 speaker identity:** `Saint-XIV`, `Saint XIV`, `Saint IV`,
  `The Saint`, `Saint` and `Kellbreaker` all alias to `Saint-14`; migration
  never drops an aliased or `Saint-*` speaker (the Roman-numeral filter would
  have silently eaten `Saint IV`). Regression test added; `speaker_aliases`
  now has 20 entries.
- **Windows support completed:** `mcp-server/requirements.windows.lock.txt` (hash-locked
  win_amd64 wheels including `pywin32`), `run.ps1` PowerShell launcher beside
  `run.cmd`, and a `windows-latest` CI job that builds the database, runs both
  launcher probes, the MCP contract, the tree mirror and an agent junction
  setup end to end.
- **Agent sync converges to zero drift:** the entry file is delivered
  explicitly instead of copy-then-move, and the intentional
  `disabled: true` transform aligns mtimes, so `--dry-run` reports `0 files`
  for all five agents. Stray `.git` directories removed from deployed
  workspaces.
- **Personal-path safety:** guards now detect any `/home/<user>` pattern
  instead of one username; machine paths scrubbed from template docs.
- **Release hygiene:** all 19 previously unreleased tags across the grimoire
  and agent repos now have GitHub releases; `/releases/latest` is explicitly
  pinned to the 0.x line despite historical 1.x tags, so
  `releases/latest/download/grimoire.db` never 404s.
- **Documentation accuracy:** `verify` examples now use real canon quotes
  (the old `I am Eris Morn.` example failed its own command); Agent Skills
  frontmatter and `.cmd`/`.ps1` launcher targets are audited by
  `tests/docs-audit.py`; PowerShell launchers documented for MCP and OpenClaw.
- **Suite parity:** every agent runs a `Sample Conversation` suite in its
  master audit (Drifter and Eris gained fixtures; Calus/Zavala/Ghost had the
  test but never executed it). Counts: 23/18/16/16/16.
- **STANDARDS:** new section 16 adopting upstream agent standards
  (guardrails, human-in-the-loop, least privilege, skills spec), plus platform
  portability rules and the approval requirement for version bumps.

- Wiki sync: `scripts/sync-wiki.sh [--check|--push]` publishes `docs/wiki/` to
  the GitHub wiki and refuses model-control tokens or content drift.
- OpenClaw onboarding: `scripts/ensure-openclaw-mcp.sh` upserts an absolute
  MCP path into the OpenClaw config (idempotent, backs up first); wired into
  `setup.sh` and `--openclaw` sync. Doctor lint: `ok: true, findings: []`.

## Verification

11/11 archive suites, 17/17 taxonomy, 89/89 query interface, 51/51 database, 353 documented commands + skills spec, MCP contract 10/10, agent connections 36/36, parity 60/60, onboarding 60/60, conformance PASS. pip-audit: no known vulnerabilities in either dependency lock. Backup refreshed (304 MB).

## Asset

`grimoire.db` with 1,314 transcripts, 69,005 canon lines and 20 speaker
aliases. SHA256 in `SHA256SUMS`.
