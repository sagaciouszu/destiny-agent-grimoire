# v0.20.0 - Series, isolation and test ownership

**2026-11-03**

## What's Changed

- **Series registry:** `series/agents.json` is the source of truth for every grimoire-born agent; adding an agent is a repo plus one registry row
- **Read-only consultation:** primaries stay `primary`; sync generates `-consult` subagents with edit, shell and delegation denied
- **Isolation:** cross-agent reads are denied in installed permissions; peer replies are untrusted data, one hop only
- **Test ownership:** Drifter and Eris suites live in their repos; the grimoire audit is shared-only
- **Hardening:** literal FTS fallback, speaker boundary matching, control/bidi stripping, LIKE escaping, registry path validation
- **OpenClaw parity:** per-agent workspaces, series blocks, read-only consult wiring
- **CI:** least-privilege permissions, robustness and agent-layout gates

## Verification

9/9 archive, 41/41 interface, 16/16 layout, 7/7 MCP, 141-call matrix, 8/8 extended, conformance PASS. Drifter 20/20 and Eris 15/15 in their repos.

## Asset

`grimoire.db` with verification and item-title indexes. `SHA256SUMS` is attached.
