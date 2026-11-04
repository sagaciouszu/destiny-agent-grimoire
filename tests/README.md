# Tests

Shared validation for the archive and the agent interface. Persona-specific
suites live in each agent repo under `tests/`; everything here is archive-wide
or shared by every agent in the series.

## Entry points

- Grimoire: `bash grimoire-master-audit.sh` (9 suites, archive-wide)
- Drifter: run tests/master-audit.sh in how-to-drift-for-agents (20 suites)
- Eris: run tests/master-audit.sh in eris-morn (15 suites)
- `resolve-workspace.sh <caller> [drifter|eris]` - layout-independent workspace
  resolution for agent suites (`lore/` may be a symlink or a clone)

## Archive integrity

- `test-db.sh` - database integrity (51 checks: tables, FTS, orphans, counts,
  entity leakage, speaker canon, provenance, `v_speakers`, `speaker_aliases`)
- `lore-integrity.sh` - archive structure (books, transcripts, cards, records)
- `lore-format.sh` - source markdown transcript format (68/68)
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
- `source-overlap-verify.py` - curated markdown vs live Ishtar, filename/slug
- `speaker-audit.py` - parse-noise regression gate for speaker names
- `sync-doc-counts.py` - rewrite documented counts from the database
  (`--check` for the CI-style staleness gate)
- `live-sample-verify.py` - on-demand live coverage probe (network)

## Agent-side suites (in each agent repo)

These moved out of the grimoire so each agent is independently deployable and
auditable. Shared gates are still imported from lore/tests/.

Drifter (how-to-drift-for-agents/tests/):

- drifter-*.sh and drifter-voice-scorer.py - voice, scenarios, quotes, modules,
  freshness, conflicts, gambit and tape simulation
- validate.sh - workspace link and quote validation
- conversation-test.sh - SQLite conversation test
- build-quote-index.py - rebuild reference/quote-inverted-index.json
- golden-voice.json and golden-voice-test.sh - fixed pass/fail snapshots
- master-audit.sh - all 20 suites

Eris (eris-morn/tests/):

- eris-*.sh and eris-voice-scorer.py - voice, scenarios, quotes, modules,
  multi-turn arc and contamination scan
- conversation-test.sh - SQLite conversation test
- golden-voice.json and golden-voice-test.sh - fixed pass/fail snapshots
- master-audit.sh - all 15 suites

## Extended (on demand)

- `extended-suite.sh` - fault injection, MCP, checksum, source, retrieval,
  item, docs and robustness gates
- `robustness-test.py` - corrupt/truncated/missing databases, edge inputs,
  read-only enforcement, 160 concurrent queries, injection attempts
- `mcp-matrix-test.py` - MCP calls across all eighteen tools (140-200 per run), 3 concurrent clients,
  strict parity with the API, clean malformed-call errors, output caps
- `checksum-test.sh` - verified download, missing checksum warning, mismatch
  rejection with no partial or installed database
- `db-source-crosscheck.py` - DB slugs vs source files, compendium coverage,
  provenance URLs, index completeness
- `retrieval-eval.py` - 15-query retrieval baseline; compares default and ranked order
- `item-audit.py` - item slugs, titles, URLs, text and optional-field coverage
- `taxonomy-deep-test.py` - tiers, classification refs, seasons, events, lore, seals,
  manifest links and API parity for the additive layers.
- `agent-connections-test.sh` - every local agent resolves the canonical DB and the
  current character/lore/seal surface; skips agents that are absent.
- `docs-audit.py` - every documented command resolves; query subcommands and flags are valid

## Onboarding and links (on demand)

- `onboarding-smoke.sh` - both agents, symlink and clone modes, fully offline:
  clone, setup, master audit, clean working tree (24 checks)
- `link-check.py` - external URL health for the READMEs (`--all` includes badges)
- `mcp-test.py` - MCP tool contract, read-only guard and stdio handshake
  (`mcp-server/.venv/bin/python tests/mcp-test.py`; skips without the venv)

## Archive utilities

- `yt-transcript.sh` / `yt-batch.sh` - caption extraction (subtitle-only)

## Scrapers (`archive/data/`)

- `archive/data/fetch_transcripts_web.py` - Ishtar transcript pages ->
  `transcripts_web.jsonl`
- `archive/data/fetch_cutscenes.py` - cutscene compilation captions ->
  `cutscenes.jsonl`

Both feed `db/migrate.py`; re-run migrate after fetching.
