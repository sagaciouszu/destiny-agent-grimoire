---
layout: page
title: Destiny Agent Grimoire
permalink: /
---

# Destiny Agent Grimoire

One canonical, agent-first Destiny lore archive: a single SQLite database with
FTS5 search, built from committed sources, with a documented quote policy and
verification gates. No external services at runtime.

The archive feeds independent character agents — **The Drifter** and **Eris Morn** —
which share one canonical lore database.

## Projects

- **Grimoire** — [destiny-agent-grimoire](https://github.com/sagaciouszu/destiny-agent-grimoire)
- **Drifter agent** — [how-to-drift-for-agents](https://github.com/sagaciouszu/how-to-drift-for-agents)
- **Eris Morn agent** — [eris-morn](https://github.com/sagaciouszu/eris-morn)

## Quick start

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
python3 db/query.py stats
```

See the tabs for details.
