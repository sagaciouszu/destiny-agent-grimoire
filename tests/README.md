# Tests

This directory contains validation scripts for the archive.

## Categories

### Archive-agnostic (test the data, not any agent persona)
- `validate.sh` - consistency check (quotes, links, index)
- `lore-integrity.sh` - archive structure (books, transcripts, index, slug/file mapping)
- `lore-quote-count.sh` - Drifter transcript line count (473)
- `lore-format.sh` - transcript format (68/68)
- `compendium-check.sh` - compendium files present and non-empty
- `ci-checks.py` - stale refs, em-dashes (agent files), personal paths, headers, circular/self deps

### Agent-integration (test a specific agent persona against this archive)
- `drifter-*` scripts - validate the Drifter agent's voice, modules, scenarios, etc.
- `drifter-master-audit.sh` (at repo root) - unified Drifter audit (17 suites)

These integration tests are kept here for backward compatibility with consumers
(e.g., how-to-drift-for-agents). They are not required for archive integrity.
