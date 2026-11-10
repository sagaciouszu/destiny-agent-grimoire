# Tests

Shared validation for the archive and the agent interface. Persona-specific
suites live in each agent repo under `tests/`; everything here is archive-wide
or shared by every agent in the series. Numbers below are descriptive only;
the authoritative counts are asserted live (`sync-doc-counts.py --check`,
`test-db.sh` against the built `db/grimoire.db`).

## Entry points

- Grimoire: `bash grimoire-master-audit.sh` (18 suites, archive-wide)
- Agents: run `bash tests/master-audit.sh` in each agent repo
- `suite-manifest-test.py` - suite loss/drift guard
- `agent-helpers/` - canonical copies of the helpers distributed byte-identically
  to every agent repo; `shared-helpers-test.sh` fails on drift or a missing
  canonical file
- `resolve-workspace.sh <caller> [drifter|eris]` - layout-independent resolution
  for agent suites (`lore/` may be a symlink or a clone)

## Archive integrity

- `test-db.sh` - database integrity (schema, FTS, orphans, counts, timeline)
- `lore-integrity.sh` - archive structure (books, transcripts, cards, records)
- `lore-format.sh` - source markdown transcript format
- `lore-quote-count.sh` - per-character transcript line counts vs the database
- `compendium-check.sh` - compendium files present and non-empty
- `ci-checks.py` - stale names, circular/self dependencies, dashes, personal
  paths, gitignored refs, headers (also invoked by `conformance.py`)
- `conformance.py` - per-file conformance across all three repos (headers, refs,
  token accuracy, persona-agnostic grimoire, tracked symlinks, README contract,
  command targets, agent document parity)
- `agent-layout-test.sh` - deployment shape: manifest-driven per-agent dirs, no
  `lore` symlink inside `agents/`, only entry agents active, companions and peer
  blocks installed from `series/agents.json`
- `sync-readme-meta.py` - stamp or check version and last-push metadata in the
  three READMEs (`--check` for CI)
- `sync-doc-counts.py` - rewrite documented counts from the database
  (`--check` for the CI-style staleness gate)
- `source-overlap-verify.py` - curated markdown vs live Ishtar, filename/slug

## Extended suite (on demand)

- `extended-suite.sh` - extended checks beyond the core suite
- `item-audit.py` - slugs, titles, URLs, optional text coverage for items
- `taxonomy-deep-test.py` - tiers, seasons, events, lore, seals, manifest links
- `caption-test.py` - game captions (`source_tier='game_caption'`): headers,
  provenance + sightings (merged lines keep every build),
  provenance, FTS+verify parity, persona canon exclusion
- `class-filter-test.py` - hunter/titan/warlock variant filtering
- `onboarding-smoke.sh` - offline clone/setup/audit on a fresh checkout

## Retrieval & MCP

- `retrieval-eval.py` - search precision evaluation (ranked corpus vs labelled
  queries; ranked-better or not, reported in the release notes)
- `mcp-test.py` / `mcp-matrix-test.py` - MCP tool contract, input bounds,
  failure modes (rate limits, error strings)
- `mcp-agent-optimization-test.py` - large-scale MCP call matrix and scoring

## Verification & filters

- `speaker-audit.py` - parse-noise regression gate for speaker names
- `persona-freshness.py` - caption-tier exclusion for persona counts
- `count-consistency.py` - persona/doc/DB agreement
- `cutscene-verify.sh` - caption corpus verification (source references, FTS mirror)
- `query-interface-test.sh` - CLI contract (search/item/list/record/...)
- `docs-audit.py` - 378 documented commands resolve; skills spec; no stale `.md` claims
- `docs-consistency.py` - cross-repo docs: stale counts/sizes, site stats snapshot,
  agent README metadata, MCP tool list, relative links (skips absent siblings)

## Notes

Tests run against a live `db/grimoire.db`; build it first:

```
python3 db/migrate.py
python3 db/enrich_lore.py && python3 db/enrich_manifest.py
python3 db/enrich_seals.py && python3 db/enrich_itemsets.py --apply
```
