---
layout: page
title: Grimoire
---

${toc}

## <img src="/destiny-agent-grimoire/assets/icons/collections.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> What the Grimoire offers {#what-the-grimoire-offers}

Canonical, agent-first Destiny lore archive. A single SQLite database with FTS5
search, built from committed sources, with a documented quote policy and
verification gates. No external services at runtime.

- **110 books** and **1,158 book entries** of Destiny lore
- **1,229 transcripts** with **71,221 dialogue lines**
- **2,889 Destiny 1 grimoire cards**
- **2,699 interactions** (short dialogue beats)
- **58,764 items** (weapons, armor, gear lore)
- **71 triumphs and seals**
- **20 curated characters** with **1,229 quote-ready lines**
- **120,731-row FTS5 index** over all content

Every content row carries provenance. Speaker aliases are canonicalized during
migration. The full contract lives in `STANDARDS.md`.

## <img src="/destiny-agent-grimoire/assets/icons/vault.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Tables {#tables}

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

## <img src="/destiny-agent-grimoire/assets/icons/pursuits.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Query interfaces {#query-interfaces}

### CLI

```bash
python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "eris" --limit 20
python3 db/query.py verify "I am Eris Morn."
python3 db/query.py item "Ace of Spades"
python3 db/query.py book "Books of Sorrow"
python3 db/query.py transcript "Crota's End"
python3 db/query.py record "Flawless"
```

Every command accepts `--json` and `--limit`/`--offset`. `verify` is the
quote-safety primitive (exit 1 when absent).

### MCP adapter

Install the typed tool adapter once:

```bash
bash mcp-server/install.sh
```

It serves read-only tools over local stdio for non-shell agents:

- `search` — FTS5 search across all content
- `character` — lines for a character
- `item` / `find-item` — item lore lookup
- `verify` — quote verification
- `book` / `transcript` — full text retrieval
- `record` — triumphs and seals
- `list` / `stats` — schema and counts

Client config snippet is printed by the installer; details in
`mcp-server/README.md`.

### Agent skill

Drop-in skill at `skills/destiny-grimoire/SKILL.md`.

## <img src="/destiny-agent-grimoire/assets/icons/traveller.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Machine-readable interface {#machine-readable-interface}

`db/capabilities.json` is a manifest of tables, views, commands and contracts.

## <img src="/destiny-agent-grimoire/assets/icons/meditations.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Compendium {#compendium}

Agent-optimized index of character dialogue extracted from transcripts.

Major characters include Drifter, Eris Morn, Emissary (Orin), Ghost, Saint-14,
Zavala, Blue (Drifter's Ghost), Shaxx, Lord Saladin, Sloane, Spider, Aunor,
Cayde-6, Osiris, Nokris, Eido, Bael and The Nine.

Full index: [compendium/index.md](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/compendium/index.md)

## Links

- [Repository](https://github.com/sagaciouszu/destiny-agent-grimoire)
- [Releases](https://github.com/sagaciouszu/destiny-agent-grimoire/releases)
- [STANDARDS.md](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/STANDARDS.md)
- [README](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/README.md)
- [MCP server](https://github.com/sagaciouszu/destiny-agent-grimoire/tree/master/mcp-server)
