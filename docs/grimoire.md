---
layout: page
title: Grimoire
---

Canonical, agent-first Destiny lore archive. A single SQLite database with FTS5
search, built from committed sources, with documented quote policy and verification
gates.

## Contents

| Table | Purpose |
|---|---|
| `books` / `book_entries` | Book-level and entry-level lore |
| `transcripts` / `transcript_lines` | Canon dialogue |
| `grimoire_cards` | Destiny 1 grimoire cards |
| `interactions` | Short dialogue beats |
| `items` | Weapons, armor, gear lore |
| `records` | Triumphs and seals |
| `characters` / `character_lines` | Curated character index |
| `fts` | FTS5 index over all content |

## Interfaces

- CLI: `python3 db/query.py search|character|item|verify|book|transcript|find-item|record|list|stats`
- MCP: `mcp-server/run.sh` (stdio, read-only)
- Skill: `skills/destiny-grimoire/SKILL.md`

## Links

- [Repository](https://github.com/sagaciouszu/destiny-agent-grimoire)
- [Releases](https://github.com/sagaciouszu/destiny-agent-grimoire/releases)
- [STANDARDS.md](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/STANDARDS.md)
