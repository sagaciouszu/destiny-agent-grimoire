# Testing and Auditing

## Archive audit

```bash
bash grimoire-master-audit.sh
```

Expected: **11 / 11 suites passed**.

| Suite | Covers |
|---|---|
| Database Integrity | tables, counts, FTS, provenance, schema |
| Compendium Files | character quote index |
| Lore Archive Integrity | book and card structure |
| Cutscene Caption Verification | caption sources and matches |
| Query Interface | 89 CLI and API checks |
| Agent Layout | OpenCode and OpenClaw layout, 39 checks |
| File Conformance | repository-wide format rules |
| Source Overlap vs Live | source and database agreement |
| Speaker Noise Gate | junk speakers and aliases |
| Agent Suite Manifests | no suite loss or drift |
| Tree Mirror | cross-platform sync replaces rsync (copy/delete/excludes) |

## Agent audits

Run inside each agent repository:

```bash
bash tests/master-audit.sh
```

| Agent | Suites |
|---|---:|
| Drifter | 22 |
| Eris | 17 |
| Calus | 15 |
| Zavala | 15 |
| Ghost | 15 |

The shared runner reads `tests/suites.json`:

```bash
bash tests/run-suites.sh
bash tests/run-suites.sh --tier core
bash tests/run-suites.sh --tier persona
bash tests/run-suites.sh --list
```

Tiers:

- `core` - shared capability gates
- `persona` - voice, scenario and character-specific suites
- `experimental` - opt-in checks

Additions are allowed. The central guard fails if a suite disappears, is
renamed, or drifts from `master-audit.sh`:

```bash
python3 tests/suite-manifest-test.py
```

## Database and query checks

```bash
bash tests/test-db.sh
bash tests/query-interface-test.sh
python3 tests/conformance.py
```

## MCP contract

```bash
mcp-server/.venv/bin/python tests/mcp-test.py
```

Expected: **10 / 10 passed**.

## Before a release

```bash
python3 db/migrate.py
python3 db/enrich_lore.py
python3 db/enrich_manifest.py
python3 db/enrich_seals.py
python3 db/enrich_itemsets.py --apply
bash grimoire-master-audit.sh
mcp-server/.venv/bin/python tests/mcp-test.py
```

Then stage the database, verify its checksum and rerun onboarding.

## CI

Grimoire CI builds the database, runs conformance, database and query checks,
robustness, agent layout, suite manifests, retrieval evaluation, documentation
and item audits, then the MCP contract and matrix.
