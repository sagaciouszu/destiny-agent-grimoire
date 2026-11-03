# {{name}} - Index

> **Depends On:** AGENTS.md
> **Token Estimate:** ~1.0K tokens

## Load tiers

| Tier | Files | Budget |
|------|-------|--------|
| Minimal | `{{id}}.md` + `{{id}}-core.md` | ~{{minimal}}K |
| Standard | + `voice/{{id}}-voice-core.md` + `core/relationships.md` | ~{{standard}}K |
| Deep | all modules | ~{{deep}}K |

## Identity

| File | Purpose |
|------|---------|
| `{{id}}.md` | platform entry and system prompt |
| `{{id}}-core.md` | consolidated identity, voice and canon reference |
| `{{id}}-voice.md` | voice calibration and representative lines |
| `SOUL.md` | one-page essence |
| `IDENTITY.md` | display identity |
| `TOOLS.md` | local and MCP interfaces |
| `AGENTS.md` | operating program |
| `README.md` | project overview |
| `RELEASE.md` | release notes |
| `INDEX.md` | this index |

## Core modules

| File | Purpose |
|------|---------|
| `core/guardrails.md` | authenticity and safety rules |
| `core/relationships.md` | how the character treats each major figure |
| `core/arcs.md` | narrative timeline |
| `core/voice-calibration.md` | concrete speech patterns |
| `core/decision-framework.md` | how the character chooses |
| `core/mood-triggers.md` | what shifts the mood |
| `core/tell-detector.md` | tells that reveal intent |
| `core/fear-hierarchy.md` | what the character fears |
| `core/threats-locations.md` | places and enemies that matter |
| `core/seasonal-awareness.md` | current season and events |
| `core/debt-ledger.md` | favors, debts and obligations |

## Voice

| File | Purpose |
|------|---------|
| `voice/{{id}}-voice-core.md` | core voice DNA |

## World

| File | Purpose |
|------|---------|
| `world/factions.md` | faction stances |
| `world/locations.md` | meaningful places |
| `world/relationships-map.md` | relationship graph |

## Reference

| File | Purpose |
|------|---------|
| `reference/knowledge-web.md` | source map and canon index |
| `reference/quote-index.md` | curated quote pointers |

## Verification

```bash
bash tests/master-audit.sh
```
