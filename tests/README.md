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

- `test-db.sh` - database integrity (35 checks: tables, FTS, orphans, counts,
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
  token accuracy, persona-agnostic grimoire, tracked symlinks)
- `source-overlap-verify.py` - curated markdown vs live Ishtar, filename/slug
- `speaker-audit.py` - parse-noise regression gate for speaker names
- `sync-doc-counts.py` - rewrite documented counts from the database
  (`--check` for the CI-style staleness gate)
- `live-sample-verify.py` - on-demand live coverage probe (network)

## Agent integration

- `drifter-*.sh`, `drifter-voice-scorer.py` - Drifter voice, scenarios, quotes,
  modules, freshness, conflicts, gambit and tape simulation
- `eris-*.sh`, `eris-voice-scorer.py` - Eris voice, scenarios, quotes, modules,
  multi-turn arc and contamination scan
- `drifter-quote-verify.sh` / `eris-quote-verify.sh` - every quoted string in the
  agent files traces to the database
- `drifter-quote-lookup.sh` - fast lookup over the Drifter `reference/quote-inverted-index.json`
  (regenerate with `tests/build-quote-index.py`, freshness gated by the module test)

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
