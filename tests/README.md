# Tests

Validation for the archive and for the two agent workspaces. Every suite here is
agent-agnostic except the explicitly named Drifter/Eris integration suites.

## Shared agent runner

- `agent-audit.sh <drifter|eris>` - one runner for both agents: per-agent voice,
  quote, module and scenario suites plus common checks (dependency headers, token
  estimates, dashes, INDEX completeness, personal paths)
- `resolve-workspace.sh <caller> [drifter|eris]` - layout-independent workspace
  resolution (`lore/` may be a symlink or a clone)
- Root wrappers: `drifter-master-audit.sh` (18 suites), `eris-master-audit.sh`
  (13 suites), `grimoire-master-audit.sh` (11 suites, archive-wide)

## Archive integrity

- `test-db.sh` - database integrity (38 checks: tables, FTS, orphans, counts,
  entity leakage, speaker canon, provenance, `v_speakers`, `speaker_aliases`)
- `lore-integrity.sh` - archive structure (books, transcripts, cards, records)
- `lore-format.sh` - source markdown transcript format (68/68)
- `lore-quote-count.sh` - per-character transcript line counts vs the database
- `compendium-check.sh` - compendium files present and non-empty
- `validate.sh` - Drifter workspace consistency (links, quotes)
- `drifter-xref-validate.sh` - Drifter cross-reference resolver
- `ci-checks.py` - stale names, circular/self dependencies, dashes, personal
  paths, gitignored refs, headers (also invoked by `conformance.py`)
- `conformance.py` - per-file conformance across all three repos (headers, refs,
  token accuracy, persona-agnostic grimoire, tracked symlinks, README contract,
  command targets, agent document parity)
- `sync-readme-meta.py` - stamp or check version and last-push metadata in the
  three READMEs (`--check` for CI)
- `source-overlap-verify.py` - curated markdown vs live Ishtar, filename/slug
- `speaker-audit.py` - parse-noise regression gate for speaker names
- `sync-doc-counts.py` - rewrite documented counts from the database
  (`--check` for the CI-style staleness gate)
- `live-sample-verify.py` - on-demand live coverage probe (network)

## Agent integration

- `drifter-*.sh`, `drifter-voice-scorer.py` - Drifter voice, scenarios, quotes,
  modules, freshness, conflicts, gambit and tape simulation
- `drifter-conflict-check.sh`, `drifter-freshness-check.sh`, `drifter-gambit-sim.sh`,
  `drifter-multiturn-test.sh`, `drifter-tape-generator.sh` - individual Drifter suites
- `eris-scenario-simulator.sh`, `eris-validate-response.sh` - individual Eris suites
- `eris-*.sh`, `eris-voice-scorer.py` - Eris voice, scenarios, quotes, modules,
  multi-turn arc and contamination scan
- `drifter-quote-verify.sh` / `eris-quote-verify.sh` - every quoted string in the
  agent files traces to the database
- `drifter-quote-lookup.sh` - fast lookup over the Drifter `reference/quote-inverted-index.json`
  (regenerate with `tests/build-quote-index.py`, freshness gated by the module test)

## Extended (on demand)

- `extended-suite.sh` - runs the four suites below plus the MCP contract
- `robustness-test.py` - corrupt/truncated/missing databases, edge inputs,
  read-only enforcement, 160 concurrent queries, injection attempts
- `mcp-matrix-test.py` - MCP calls across all twelve tools (140-200 per run), 3 concurrent clients,
  strict parity with the API, clean malformed-call errors, output caps
- `checksum-test.sh` - verified download, missing checksum warning, mismatch
  rejection with no partial or installed database
- `db-source-crosscheck.py` - DB slugs vs source files, compendium coverage,
  provenance URLs, index completeness
- `retrieval-eval.py` - 15-query retrieval baseline; compares default and ranked order
- `item-audit.py` - item slugs, titles, URLs, text and optional-field coverage
- `docs-audit.py` - every documented command resolves; query subcommands and flags are valid

## Onboarding and links (on demand)

- `onboarding-smoke.sh` - both agents, symlink and clone modes, fully offline:
  clone, setup, audit, clean working tree (24 checks)
- `link-check.py` - external URL health for the READMEs (`--all` includes badges)
- `mcp-test.py` - MCP tool contract, read-only guard and stdio handshake
  (`mcp-server/.venv/bin/python tests/mcp-test.py`; skips without the venv)

## Standalone utilities

- `drifter-coin.sh` - in-character coin flip for decisions
- `drifter-load.sh` - print a tiered load profile (minimal/standard/deep)
- `drifter-pre-response.sh` - pre-response validation pipeline
- `drifter-story-generator.sh` - story scaffold from a topic
- `yt-transcript.sh` / `yt-batch.sh` - caption extraction (subtitle-only)

## Scrapers (`archive/data/`)

- `archive/data/fetch_transcripts_web.py` - Ishtar transcript pages ->
  `transcripts_web.jsonl`
- `archive/data/fetch_cutscenes.py` - cutscene compilation captions ->
  `cutscenes.jsonl`

Both feed `db/migrate.py`; re-run migrate after fetching.
