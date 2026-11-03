---
layout: page
title: Getting Started
---

## Prerequisites

- `python3` 3.8+
- `git`
- ~260 MB disk

## Install

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
```

## Get the database

Download the prebuilt release asset:

```bash
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
```

Or build locally:

```bash
python3 db/migrate.py
```

## Query

```bash
python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "eris" --limit 20
python3 db/query.py verify "I am Eris Morn."
```

## Agent setup

Each agent repo contains a `setup.sh` that links to this archive and bootstraps the
database.
