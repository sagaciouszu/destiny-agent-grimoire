---
layout: page
title: Getting Started
---

* Table of contents
{:toc}

## <img src="/destiny-agent-grimoire/assets/icons/traveller.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Prerequisites {#prerequisites}

- `python3` 3.8+
- `git`
- ~260 MB disk

## <img src="/destiny-agent-grimoire/assets/icons/collections.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Install {#install}

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
```

## <img src="/destiny-agent-grimoire/assets/icons/ghost.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Get the database {#get-the-database}

Download the prebuilt release asset:

```bash
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
```

Or build locally:

```bash
python3 db/migrate.py
```

## <img src="/destiny-agent-grimoire/assets/icons/pursuits.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Query {#query}

```bash
python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "eris" --limit 20
python3 db/query.py verify "I am Eris Morn."
```

## <img src="/destiny-agent-grimoire/assets/icons/ghost.svg" class="inline h-5 w-5 text-white align-text-bottom" alt=""> Agent setup {#agent-setup}

Each agent repo contains a `setup.sh` that links to this archive and bootstraps the
database.
