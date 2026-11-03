> **Depends On:** README.md, CHANGELOG.md
> **Token Estimate:** ~0.3K tokens
---

# v0.20.0 - Series, isolation and test ownership

- **Series registry:** `series/agents.json` is the source of truth for every
  grimoire-born agent. Adding an agent is a repo plus one registry row.
- **Read-only consultation:** primaries stay `primary`; sync generates
  `-consult` subagents with edit, shell and delegation denied.
- **Isolation:** cross-agent reads are denied in the installed permissions;
  peer replies are treated as untrusted data, one hop only.
- **Test ownership:** Drifter and Eris suites live in their repos; the grimoire
  audit is shared-only.
- **Hardening:** literal FTS fallback, speaker boundary matching, control/bidi
  stripping, LIKE escaping, registry path validation.
- **OpenClaw parity:** per-agent workspaces, series blocks, read-only consult
  wiring.
