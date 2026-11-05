# v0.27.0 - Windows portability, suite manifests and wiki

**2026-11-05**

## What's Changed

- **Seasons 27-28 covered:** Reclamation (27 lines) and Monument of Triumph
  (202 lines); all 28 seasons now have a transcript. Crota's End and Wrath of
  the Machine confirmed `no_dialogue`.
- **Windows support (issues #1-#3):** `run.cmd` launcher, venv-layout detection,
  rsync-free tree mirror for agent sync, and symlink -> junction -> clone
  fallback in every setup script.
- **MCP probe:** `bash mcp-server/probe.sh` performs a real handshake and
  reports the 18 tools; OpenClaw absolute-path guidance documented.
- **Suite manifests:** every agent keeps its suites in `tests/suites.json`; a
  central guard fails on any suite loss or drift.
- **Wiki:** versioned, copyedited operator documentation under `docs/wiki/`.
- **External link check:** schedule removed; runs after deploys, on pull
  requests and on manual dispatch.

## Verification

11/11 archive suites, 89/89 query interface, 51/51 database, 16/16 taxonomy, 10/10 MCP contract, agent connections 36/36, parity 60/60, onboarding 60/60, conformance PASS.

## Asset

`grimoire.db` with 1,314 transcripts and 69,005 canon lines. SHA256 in
`SHA256SUMS`.
