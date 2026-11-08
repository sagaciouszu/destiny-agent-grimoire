# Reference Commands

## Clone and first run

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
python3 db/migrate.py
python3 db/query.py stats
```

## Database

```bash
python3 db/migrate.py
python3 db/enrich_lore.py
python3 db/enrich_manifest.py
python3 db/enrich_seals.py
python3 db/enrich_itemsets.py --apply
bash tests/test-db.sh
```

## Query

```bash
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "Eris Morn" --limit 20
python3 db/query.py transcript "Contact - Io" --speaker "Drifter"
python3 db/query.py activity salvations-edge
python3 db/query.py event festival-of-the-lost
python3 db/query.py coverage
python3 db/query.py stats
```

## Verify quotes

```bash
python3 db/query.py verify "Absolutely not." --speaker "Eris Morn" --exact
python3 db/query.py verify-many "Absolutely not." "You did well to find this point of infestation." --speaker "Eris Morn"
```

## Agents

```bash
bash scripts/sync-live-agents.sh
bash scripts/sync-live-agents.sh --dry-run
bash scripts/sync-live-agents.sh --openclaw
```

Per-agent:

```bash
cd destiny-agent-eris-morn
bash setup.sh ../destiny-agent-grimoire --no-mcp
bash tests/master-audit.sh
bash tests/run-suites.sh
bash tests/run-suites.sh --tier core
```

## MCP

```bash
bash mcp-server/install.sh
./mcp-server/run.sh
mcp-server/.venv/bin/python tests/mcp-test.py
```

## Tests

```bash
bash grimoire-master-audit.sh
python3 tests/conformance.py
bash tests/test-db.sh
bash tests/query-interface-test.sh
bash tests/agent-layout-test.sh
python3 tests/suite-manifest-test.py
mcp-server/.venv/bin/python tests/mcp-test.py
```

## Maintenance

```bash
python3 tests/sync-doc-counts.py
python3 tests/sync-readme-meta.py
python3 scripts/coverage-report.py
bash scripts/backup.sh
```

## Release

```bash
bash scripts/release-stage.sh <version>
git tag -a v<version> -m "v<version>"
git push origin master
git push origin v<version>
gh release create v<version> <staged>/grimoire.db <staged>/SHA256SUMS \
  --title "v<version>" --notes-file RELEASE.md
```

## Useful environment variables

| Variable | Purpose |
|---|---|
| `GRIMOIRE_DB` | alternate database path |
| `AGENT_REPOS_DIR` | parent directory for agent repositories |
| `SERIES_MANIFEST` | alternate agent registry |
| `OPENCODE_AGENTS` | OpenCode agent destination |
| `OPENCLAW_ROOT` | OpenClaw root |
| `NO_RELOAD=1` | skip OpenCode reload after sync |
| `LORE` | alternate lore mount for agent tests |
| `WORKSPACE` | alternate agent workspace for tests |
