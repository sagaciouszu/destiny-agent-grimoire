# Standards

> **Depends On:** none (standards reference)
> **Token Estimate:** ~10.3K tokens

The contract every file, script, and database row in this repository must meet.
Verification gates (section 7) enforce these rules; a change that breaks them is
a change that is not done.

## 1. Scope

- `destiny-agent-grimoire` is agent-agnostic: no persona, no agent-specific
  rules.
- The consumer agents listed in `series/agents.json` reference the database
  through `lore/`: a symlink on Unix, a junction or clone on Windows. They own
  their personas; this repo owns canon.
- Documentation lives in two tiers: `README.md` and `docs/wiki/` are written
  for humans; `skills/` and each agent's AGENTS.md/TOOLS.md are written
  for agents (commands first, prose second, no narrative detours).
- `source/` is the ingestion corpus (verbatim lore, formatting-normalized).
  `archive/` holds raw scrape output. `db/` holds the migration and interface.
- The database (`db/grimoire.db`) is a build artifact: never committed,
  rebuilt from `source/` + `archive/` by `python3 db/migrate.py`, published as
  a release asset.

### Agnostic contract

The archive is one shared service for many agents. It must not encode a
preferred persona, voice or workflow.

- **One roster source.** `series/agents.json` is the only list of agents,
  repositories, entry files and peer relationships. Shared scripts read it;
  they never hardcode a repository name, a default agent or a hand-copied
  roster. `tests/count-consistency.py` is the reference implementation.
- **No persona default in shared files.** `README.md`, `STANDARDS.md`,
  `db/README.md`, `scripts/README.md`, `mcp-server/README.md`, `skills/**` and
  `docs/wiki/**` describe the contract, not one agent. A corpus speaker may
  appear in an example only to demonstrate a real query, and the example is
  labelled illustrative; it never implies a preferred agent, voice or memory.
- **Persona material stays with its owner.** SOUL.md, voice guides,
  relationships, private memory and agent-specific tests live in the agent
  repository. The archive may validate the contract; it never writes a persona
  and never carries per-agent rules in a shared gate.
- **Discovered speakers are not canon.** `v_speakers` is a discovery view of
  every observed speaker, including caption-only names. It is not a canon
  roster and must not be presented as one. Canon membership is the `characters`
  table plus the `persona.json` of an agent that owns that persona.
- **Caption tier is canon, not persona canon.** Captions are searchable and
  quotable. `persona.json` `canon_lines` excludes them. `--canon-only` means
  "exclude optional and variant lines", never "exclude captions"; documentation
  must state that distinction where the flag appears.
- **Cross-agent collaboration is data.** The registry defines peers and the
  read-only `-consult` copies. There is no shared private memory, no shared
  editable workspace and no implicit delegation beyond one hop.
- **The site publishes the roster.** Naming the production agents on the site
  is publishing registry data, not a default. Site templates must still render
  an arbitrary registry row and must not assume one agent.

### Corpus scope (era coverage)

The corpus covers **Destiny 2 from launch (Sep 2017) through the current live
build at the time a row is added** - campaigns, expansions, seasons, episodes
and seasonal events. Destiny 1 content (Dark Below, House of Wolves, The
Taken King, Rise of Iron and D1 expansions in D2) is included where canon
verbatim text exists; it is the only D1 coverage.

**Sourcing rule:** any D2 build from launch to the current live build is a
legitimate source, but each piece of content may only be sourced from a build
that still shipped it. A post-vault build must never be used as the source
for vaulted content; use the era transcripts/manifests that captured it at
its time (Web captures are the primary source for DCV-era content; the live
build covers everything that still ships).

**Provenance is labeled per build.** Every raw capture and curated row carries
the build/id it came from (`sunrise-pre-bl`, `build-25932352`, ...);
`caption_provenance` and friends never mix builds silently. Build identities,
versions and the extraction-tier to provenance mapping live in
`docs/process/Builds.md`.

**A build is not a proxy for an earlier build.** The live client is the
current game with years of Bungie changes on top of its content: recast
voices, rewritten lines, moved items and dropped activities. Text that
differs from an earlier era's capture is drift, not an error — canon lines
alike keep the era capture text; a drift log is the deliverable, never an
inline rewrite. The live build (`build-25932352`) is legitimate for
current-era extraction, 2024+ gameplay labels and verification, never as
ground truth for what Beyond Light shipped.

**2024+ speaker-name gameplay subtitles** are accepted as speaker attribution
**with provenance labels** (`speaker_source` naming the live build), but:

- they apply only to gameplay subtitles - cinematics are excluded by Bungie's
  own implementation and this standard mirrors that exclusion,
- they are never claimed as fact without corroboration for anything canon-
  affecting; attribution stays evidence-first,
- they never rewrite persona canon counts (the caption exclusion still holds).

A corpus that claims coverage it does not have is invalid; era expansion only
lands with the gate suite green and release notes naming the sources.

**String-bank text is not subtitle captions.** A live `w64_sr_globals` package
carries the game's whole text surface, not a subtitle track: quest prose,
objectives, item and perk copy, callouts, and some dialogue, all in one table.
When it is ingested into the caption tier:

- the build is the authoritative provenance, not the bucket: `source_build`
  says which client shipped the line; `kind` (`dialogue`, `narration`,
  `objective`) is a **heuristic** label from punctuation and attribution, and
  is never presented as a build-side fact;
- a line that carries its own attribution (`"..." —Name`) is dialogue and its
  speaker is that name; nothing else is attributed;
- mechanical copy (perk and modifier stat text) and fragments of item entries
  the corpus already holds are **excluded**, because a lore corpus must not
  return the same text twice in two shapes;
- one build's string banks are not era-pure. A single package can hold text
  from several expansions and seasons; package order is not chronology and
  must never be used to date a line.

## 2. Repository connection matrix

| From | To | Mechanism |
|------|----|-----------|
| agent `README`/`INDEX`/`AGENTS`/`TOOLS`/agent def | lore database | `lore/db/grimoire.db`, `python3 db/query.py` |
| agent setup.sh | this repo | links `lore/` (symlink -> Windows junction -> clone); bootstraps the DB (release asset or build); points OpenClaw's MCP entry at the checkout |
| agent `.gitignore` | runtime memory | USER.md, `core/*memory*`, core/journal.md never leave the machine |
| agent `tests/` suites | agent workspace | lore/tests/resolve-workspace.sh (layout-independent; `lore/` may be symlink or clone) |
| `db/migrate.py` | sources | `source/{books,transcripts,cards,records}` + `archive/data/*.jsonl` |
| `scripts/ishtar-timeline.py` | snapshot | `source/ishtar-timeline.json` (45 eras, 800 source links; regenerate on demand with `--fetch`) |
| `db/query.py` | database | CLI wrapper over `db/api.py`; every query subcommand in section 8 |
| `tests/sync-doc-counts.py` | archive and agent repos | rewrites database and suite-check counts from their live sources (`--check` mode fails on drift) |
| `tests/sync-readme-meta.py` | all repos | stamps README `Version` / `Last push` from git tag / HEAD date (`--check` mode fails on drift) |
| `scripts/sync-wiki.sh` | wiki clone | copies `docs/wiki/*.md`, fails on model-control tokens or missing pages (`--check`/`--push`) |
| release workflow | consumers | `db/grimoire.db` attached as a release asset (checksum-verified); `grimoire.db.xz` and `grimoire.db.gz` published by `mcp-server/run.sh` on `release.published` |

### Symlinks

- `lore/` is runtime state, not repository content: setup.sh creates it as a
  symlink to a local checkout, or clones the repo in place. It is gitignored in
  both agent repos.
- No tracked symlinks in any repository. A tracked absolute symlink (for
  example `lore -> /home/<user>/...`) breaks every clone: it arrives dangling,
  and setup.sh would otherwise mistrust it as an existing archive.
- setup.sh treats a dangling `lore/` symlink as absent: it removes it and then
  symlinks or clones as requested.
- A symlink target is never a commit-time fact; it is resolved per machine.

## 3. Database contract

Every table below is part of the schema contract. `tests/test-db.sh` (68 checks)
verifies schema presence, counts, the `timeline_chapters` vocabulary, transcript
timeline coverage, the transcript/FTS `timeline` mirror, `character_lines`
inheritance, and `db/capabilities.json` sync.

| Table | Required | Optional (may be empty) | Notes |
|-------|----------|--------------------------|-------|
| `books` | slug, title | source_url, entry_count, timeline, timeline_basis | slugs match live `categories/book-<slug>` (2 documented exemptions); `timeline_basis` is `classification`, `release_name`, or `ishtar_timeline` |
| `book_entries` | book_id, body | title (fallback to book title), seq | provenance via parent book |
| `transcripts` | slug, title | release, characters, arc, source_url, source_tier, timeline, timeline_basis, lang | release empty when the source lacks it; `source_tier` records provenance precedence; `timeline` is the in-universe story chapter (see `timeline_chapters`), NULL when unknown; `lang` is the document language (`en` today, caption languages drop in as data) |
| `transcript_lines` | transcript_id, seq, speaker, line, norm_line | is_stage_dir, section, is_optional, class_tag, speaker_source | seq contiguous from 0; class_tag is hunter, titan or warlock; speaker_source is nullable, set for caption lines with attribution provenance |
| `caption_provenance` | line_id | hash, kind, source_pkg, source_entry, bank_entry | one row per caption line (and per canon line a caption reuses): StringReference hash, package/entry/bank origin and table kind; never guesses |
| `caption_sightings` | line_id, source_build, source_slug, line_ord | source_pkg, source_entry, bank_entry, record_index, record_part, kind, hash, captured_at | one row per processed caption record line: every build/package observation, including lines whose provenance row names an earlier build; never collapses distinct sunrise lines |
| `grimoire_cards` | slug, title, body, source_url | game, timeline, timeline_basis | D1 cards only; timeline via `source/ishtar-timeline.json` (110 on-timeline cards), NULL otherwise |
| `interactions` | slug, title, text | speaker, release, source_url, timeline, timeline_basis | speaker may be empty (narrated scenes) |
| `items` | slug, title | text, release, item_type, source_url, timeline, timeline_basis | 16k stat-only items have no lore text by design; ~600 junk release strings stay NULL |
| `records` | slug, title, body | release, source_url, timeline, timeline_basis | timeline prefers `document_classification` over the release string |
| `characters` | name, slug | | curated character index (compendium) |
| `character_lines` | character_id, text, source_type, source_slug | norm_text, timeline | source_slug must resolve in `transcripts`; timeline inherited from it |
| `speaker_aliases` | alias, canonical | | alias -> canonical speaker mapping |
| `entities` | canonical, norm_key, kind, confidence, reviewed | | entity web; one row per named character, power, faction or place (88 rows); never rewrites canon |
| `entity_aliases` | entity_id, alias, norm_alias, weight, confidence, requires_ctx, reviewed | | attested name variants; `norm_alias` is the resolver key |
| `entity_links` | entity_id, kind, ref, weight, match, build_id | | ref resolves to exactly one parent row at build time; `UNIQUE (entity_id, kind, ref)` |
| `entity_relations` | entity_id, relation, target_entity_id, source | | `adjacent_to` (Siren of Riven -> Riven), `related_to` (Gardener -> The Traveler, Winnower -> The Darkness) |
| `entity_build_meta` | key, value | | build audit trail (build_id, hashes, timings) |
| `fts` | | | exactly one row per indexed content row (1:1); carries `timeline` UNINDEXED |
| `item_title_fts` | | | item titles for fast name lookup |
| `lore_entries` | id, hash, title | subtitle, body, norm_body, source, source_url, is_duplicate, duplicate_of | `hash` is unique; `source` defaults `bungie_manifest` |
| `lore_entry_items` | lore_hash, item_title | | PRIMARY KEY (lore_hash, item_title) |
| `expansions` | slug, name | game, year, release_date, vaulted | catalogue, seeded from `db/taxonomy.py` |
| `seasons` | slug, season_number, name | season_type, act, destiny_year, expansion_slug, start_date, end_date, vaulted | official numeric slot, unique; never renumber |
| `activities` | slug, name, activity_type | season_slug, event_slug, expansion_slug, vaulted | catalogue |
| `events` | slug, name | event_type, first_year, last_year, recurring, vaulted, notes | rotating events |
| `event_occurrences` | event_slug, year | season_slug, start_date, end_date, vaulted | one row per event-year |
| `transcript_classification` | transcript_id, confidence | activity_slug, activity_type, season_slug, act, event_slug, expansion_slug, evidence | additive; never rewrites canon |
| `item_classification` | item_id, confidence | season_slug, event_slug, expansion_slug, evidence | additive |
| `document_classification` | source, source_slug | season_slug, event_slug, expansion_slug, confidence, evidence | books and records |
| `coverage_notes` | entity_type, slug, status | evidence, source_url | one row per zero-coverage activity, event or season; status is `covered`, `partial_transcript`, `narration_only`, `dialogue_source_missing`, `no_dialogue` or `missing` |

Public views: `v_speakers` is discovery (423 observed speakers, including caption-only names); `v_canon_speakers` is persona-canon membership (230 speakers with at least one non-stage, non-optional, non-caption line); the entity and taxonomy views serve resolution and coverage. A view row is not a persona and never rewrites canon.

### Taxonomy rules

- Four independent axes: expansion, season/episode, activity, event. Do not
  overload `release` or `arc`; they remain fallback text only.
- `seasons.season_number` is Bungie's official number. Episodes use
  `season_type='episode'` with their numeric slot; never renumber.
- Events repeat across seasons, so occurrence rows carry the year and season.
- `confidence` is `explicit`, `derived`, `manual` or `unknown`. `unknown` is a
  valid terminal state; never guess to make coverage look better.
- `vaulted=1` marks removed content; vaulted rows stay searchable.
- A Destiny 1 expansion (`destiny-1` through `age-of-triumph`) never inherits a
  Destiny 2 season from an activity that was later reprised.
- Zero coverage is never a blank: every activity, event and season with no
  transcript carries a `coverage_notes` row. Rows are additive; removing one
  requires a source that actually closes the gap.
- Full model and query examples: `docs/TAXONOMY.md`.

### Timeline chapters

`timeline_chapters` holds 23 rank-ordered story chapters (rank 1 =
Pre-History through rank 23 = Renegades). Rows carry the chapter slug in their
`timeline` column; join this table for rank/label. NULL `timeline` means
unknown position (honest gap, not a default). Dialogue follows the when-spoken
rule: an explicitly past-set scene beats its release position.

### Source hierarchy

Ishtar Collective is the archival primary; Destinypedia is corroboration.

Reference snapshot: `source/ishtar-timeline.json` is the checked-in copy of
the Ishtar timeline (45 eras, 800 source links; regenerate on demand with
`python3 scripts/ishtar-timeline.py --fetch`). The build consumes it offline
to time books, records, items and cards (`timeline_basis = ishtar_timeline`);
`python3 scripts/ishtar-timeline.py --report db/grimoire.db` diffs its
about-time eras against the when-spoken chapters of dialogue rows for
curated-override review.

### Optional and variant lines

Ishtar's transcript guide defines `// OPTIONAL` blocks for alternatives, class
callouts and variants. These are stored with `is_optional=1`; section/location
headers from `++` are stored in `section`; class-exclusive lines carry
`class_tag = hunter|titan|warlock`. Agents quote non-optional lines by default,
and `--class` adds the chosen class variants.

### Persona canon

`persona.json` `canon_lines` counts the corpus a persona was built from: exact
speaker, `is_stage_dir=0`, `is_optional=0`, **excluding game captions**
(`source_tier='game_caption'`). Captions are searchable, quotable canon, but
they are not part of a persona's curated voice count - so a caption drop never
rewrites an agent persona. The identical predicate is used by
`tests/persona-freshness.py` (every agent repo),
`tests/count-consistency.py`, `character_info.spoken_lines` in `db/api.py`, and
the persona generator that ships with the agent template.

### Extracted game data

Raw game packages, audio, string tables, subtitle exports and Bungie manifest
dumps are **local-only**. They must never be committed, attached to a release or
copied into an agent workspace. `.gitignore` covers
`archive/data/manifest/`, `archive/data/game/`, `archive/data/subtitles/` and
`*.pkg`.

Only curated material may be committed, with provenance naming the local build,
for example `- Source: local game files (<build>)`. That includes the scraped
JSONL corpora under `archive/data/` and the curated caption corpus
`archive/data/captions.jsonl` - English lines only, with speaker attribution,
activity facets, dedup verdicts and the build id recorded in each record
(builds seen to date: `sunrise-pre-bl`, then `build-25932352`, each labeled;
see `docs/process/Builds.md`). The raw subtitle exports it is derived from stay in
`archive/data/subtitles/` and remain gitignored. Extracted text is evidence for
curation, not a redistributable asset: commit the curated rows, never the raw
dump.

### Generated artifacts and single sources

Counts, versions, rosters and wiki pages have one producer. A consumer reads
the producer's output; it never hand-maintains a second copy.

| Artifact | Producer | Consumer | Guard |
|---|---|---|---|
| `db/grimoire.db` | `db/migrate.py` then the four `db/enrich_*.py` steps | CLI, API, MCP, agents, releases | `tests/test-db.sh`; release `SHA256SUMS` |
| `db/capabilities.json` | hand-maintained interface manifest | docs, MCP, site export | `tests/test-db.sh` compares every table and view |
| README count claims | `tests/sync-doc-counts.py` | every README, wiki page, skill, site | `--check`; `tests/docs-consistency.py` |
| README version/date line | `tests/sync-readme-meta.py` | every repository README | `--check`; `tests/docs-consistency.py` |
| `docs/wiki/*.md` | repo docs, pushed by `scripts/sync-wiki.sh` | GitHub wiki | `--check`; conformance and docs-consistency |
| site `../destiny-agent-grimoire-site/_data/grimoire.json` | `scripts/export-site-stats.py` | every site stat block | `../destiny-agent-grimoire-site/scripts/check-stats.py`; docs-consistency |
| site `../destiny-agent-grimoire-site/_data/agents.js` | hand-maintained roster and audit totals | persona pages | `../destiny-agent-grimoire-site/scripts/check-roster.py` |
| `series/agents.json` | hand-maintained roster | sync, layout, conformance, counts | layout, count-consistency, conformance |
| agent `reference/knowledge-web.md` snapshot | `scripts/generate-knowledge-web.py --apply` | agents, docs-consistency | `--check`; master audit |

Rules:

- A new count or roster claim is added to the producer and the guard in the
  same change. A literal with no producer is a future stale number.
- Historical release notes and changelogs are exempt: they record what shipped,
  not what is current.
- `--check` modes are the gate; write modes are maintenance commands run before
  a release, never part of an agent's runtime.

## 4. Naming

- Slugs: lowercase, hyphenated, taken from the live page slug wherever one
  exists.
- Non-Ishtar sources keep their own slug and provenance (`youtube-*`,
  `weblore-*`, `ingame-quotes-*`, `cutscene-*`).
- Filename must match the `- Source:` slug (allowlisted, documented renames
  only).
- Speakers use canonical names. `SPEAKER_ALIASES` in `db/migrate.py` is the
  single source of truth, applied at migration; new aliases go there, never
  into a verifier. Current entries include `Commander Zavala -> Zavala`,
  `Cayde -> Cayde-6`, `Eris -> Eris Morn`, `Ikora Rey -> Ikora`,
  `Chiomi Esi -> Chioma Esi`, `Queen Mara Sov -> Mara Sov`,
  `The Drifter -> Drifter`, `The Crow -> Crow` and `Emperor Calus -> Calus`.
  One speaker, one name: if two names identify the same character, add an
  alias instead of splitting the corpus.
- Quest/step titles are not speakers. Web scrapers sometimes parse titles such
  as `Path of the Splicer II`, `Into the Depths VI` or `Act I` as speakers;
  migration drops those rows. The Roman-numeral rule never drops a mapped
  character: a speaker that resolves through `SPEAKER_ALIASES` is kept, and
  every `Saint-*` speaker is kept outright. Add the alias before introducing a
  character whose name ends in a numeral; a dropped row is unrecoverable, a
  kept row can always be aliased later.
- Contextual qualifiers are allowed and kept: `Drifter (Tape 1)`,
  `Eris Morn (communion)`, `Blue (about Drifter's Ghost)`. LIKE queries match
  the base name, so consumers never need the qualifier.

## 5. Normalization

One function, implemented identically in `db/migrate.py` and every verifier:
lowercase, `...` -> `...`, `'` apostrophe, dashes to `-`, non-alphanumerics to
space, whitespace collapse, trim. `norm_*` columns store its output and must
match a recomputation of their source text.

## 6. Quoting policy (agents)

- A quote must trace to a speaker-attributed canon line or verbatim lore text.
  `verify` accepts `--speaker` (attribution) and `--exact` (full row, not
  fragment); agents should use both when quoting dialogue.
- Do not present another character's line as the persona's voice. Exchange
  context, reported speech, and impressions must be explicitly attributed.
- When a quote cannot be traced: unquote it, do not delete it.
- Unverified count must stay zero in every shipped audit.

## 7. Verification gates

| Gate | Enforces |
|------|----------|
| `tests/test-db.sh` | schema integrity, counts, no orphans, no entity leakage, character provenance, canonical speakers, card provenance, live meta stamp, class-tag and normalization invariants, capabilities sync (68 checks) |
| `tests/lore-integrity.sh` | source archive structure, book/transcript/card/record counts |
| `tests/lore-format.sh` | transcript markdown format |
| `tests/cutscene-verify.sh` | caption corroboration, encoding, cross-video consistency, attribution |
| `tests/query-interface-test.sh` | CLI and API surface, 97 checks |
| `tests/db-source-crosscheck.py` | database slugs vs source files, provenance URLs, index completeness |
| `tests/caption-test.py` | game captions: headers/language, StringReference provenance, no duplicate canon text, curated activity facets, FTS/verification parity, demoted stat lines, caption search, persona canon exclusion |
| `tests/speaker-audit.py` | reclassified parse noise must not reappear |
| `tests/sync-doc-counts.py --check` | docs counts match the database |
| `tests/sync-readme-meta.py --check` | README metadata matches git tag / HEAD date |
| `tests/docs-consistency.py` | stale counts/sizes, site snapshot, agent metadata, MCP README parity, relative links across every repo |
| `tests/agnostic-test.py` | shared scripts read `series/agents.json`; no hardcoded agent repo in a shared executable |
| `tests/agent-access-test.py` | setup dry-run and dangling links, missing-database failure, read-only database, site roster parity |
| `scripts/generate-knowledge-web.py --check` | each agent knowledge web carries a canon snapshot that matches the database |
| each agent repo tests/master-audit.sh | agent-side suites (voice, quotes, modules, conversation, golden snapshots) plus shared structure checks |
| `tests/mcp-test.py` (on demand, needs `mcp-server/.venv`) | MCP tools, both launchers, probe handshake, read-only guard, stdio, CLI-parity tools, stats/live agreement (12/12 checks) |
| `tests/mcp-agent-optimization-test.py` (on demand, needs `mcp-server/.venv`) | LLM-facing surface: descriptions name every parameter, actionable ToolErrors, 25-token snippets, limit/offset clamps, resource caps, one-call item lookups, spoken_lines counts (25 checks) |
| `tests/mcp-matrix-test.py` (on demand, needs `mcp-server/.venv`) | MCP calls across all 22 tools (161 calls), 3 concurrent clients, strict API parity, clean malformed-call errors |
| `tests/check-agent-structure.py <deps\|tokens\|dashes\|index\|paths> <workspace>` | per-agent: deps resolve, token accuracy, no em/en-dashes, INDEX lists every module and every reference resolves, no personal paths |
| `tests/robustness-test.py` (on demand) | corrupt/truncated/missing databases, edge inputs, read-only enforcement, 160 concurrent queries, injection attempts |
| `tests/agent-layout-test.sh` | OpenCode and OpenClaw layout, registry and peer blocks (108 checks) |
| `tests/agent-parity-test.sh` | every present agent exposes the same shared capabilities |
| `tests/onboarding-smoke.sh` | clone + setup + master audit for every local agent, offline |
| `tests/suite-manifest-test.py` | per-agent suite manifests match master-audit and the no-loss baseline |
| `tests/mirror-tree-test.py` | cross-platform tree mirror used by agent sync (replaces rsync) |
| `tests/conformance.py` | per-file headers, token accuracy, refs, persona-agnosticism; runs `ci-checks` per agent repo |
| `tests/ci-checks.py <check> <workspace>` (via conformance) | stale names, circular/self dependencies, headers, em-dashes, personal paths, gitignored refs in instructions |

Live probes (on demand, network): `tests/live-sample-verify.py` samples every
content type against Ishtar; each agent repo's voice-consistency suite runs
cross-character attribution checks.

## 8. Agent interface contract

- Interface: `python3 db/query.py` with one of `search`, `character`,
  `character_info`, `item`, `book`, `transcript`, `find_item`, `record`,
  `verify`, `verify_many`, `list`, `activity`, `event`, `lore`, `seal`,
  `seals`, `coverage`, `stats`, `entity`. `sqlite3` is the escape hatch. No
  markdown parsing at runtime.
- Shared query layer: `db/api.py` returns data; the CLI formats it and the MCP
  server exposes the same functions as typed tools. One implementation.
- MCP: `mcp-server/` is an optional stdio adapter using the official SDK. It is
  read-only, has no SQL tool, clamps limits to 1-100 and trims text to 4000
  chars. It is stdio-only by design: no listener and no auth surface; hosting
  requires an authenticated wrapper.
  - Install with `bash mcp-server/install.sh`, or `./setup.sh --mcp` in an
    agent workspace (the interactive prompt also offers it). The adapter
    belongs to the archive, so one install serves every agent; the venv is
    gitignored and the CLI stays dependency-free.
  - 22 tools: `search`, `entity`, `character`, `character_info`, `item`, `verify`,
    `verify_many`, `list_records`, `stats`, `book`, `transcript`, `find_item`,
    `activities`, `activity`, `seasons`, `events`, `event`, `coverage`,
    `record`, `seals`, `seal`, `lore`.
  - 9 resources: `grimoire://books`, `grimoire://characters`,
    `grimoire://records`, `grimoire://stats`, `grimoire://activities`,
    `grimoire://seasons`, `grimoire://events`, `grimoire://coverage`,
    `grimoire://entities`.
  - 4 templates: `grimoire://book/{slug}`, `grimoire://transcript/{slug}`,
    `grimoire://character/{slug}`, `grimoire://record/{slug}`.
  - 2 prompts: `quote_safe_lookup`, `character_brief`.
  - Limits: `MAX_TEXT=4000` (tool result text), `MCP_MAX_LIMIT=100` (rows),
    `MAX_TOPIC=300` (prompt topic), `MAX_RESOURCE=16000` (resource payload),
    offset clamp 10000.
- Coverage answers are self-describing: `coverage` and `activity` return
  `coverage_status` (`covered`, `partial_transcript`, `narration_only`,
  `dialogue_source_missing`, `no_dialogue` or `missing`) plus `coverage_notes`
  evidence. Surface the status verbatim; never imply that a partial transcript
  is complete.
- Every command supports `--json`; search returns snippets unless `--full`;
  `verify` exits 1 when a quote is absent (quote-safety primitive).
- FTS is the search surface: `fts` holds exactly the indexable rows, `MATCH`
  syntax, porter stemming.
- Output budget: `--limit` on every query; agents should assume 20-40 rows per
  call and never dump tables.
- Memory files are runtime state, never canon: personalities live in the agent
  repos, canon lives in the database.
- Nothing in this repo may assume a specific agent platform. Files are plain
  markdown/yaml/binary data with the documented contracts above.

## 9. Agent workspace contract

All six agent repositories follow one workspace contract so a single method
serves every agent.

- Root: AGENTS.md, INDEX.md, SOUL.md, IDENTITY.md, TOOLS.md,
  `<agent>.md` (platform entry), `<agent>-core.md`, `<agent>-voice.md`,
  `README.md`, `RELEASE.md`.
- Shared directories: `core/`, `voice/`, `world/`, `reference/`.
- setup.sh ships in two lengths (full and short) but always performs the same
  contract: seed runtime memory from templates, link `lore/` (symlink -> Windows
  junction -> clone, in that order), bootstrap the database (release asset or
  local build, checksum-verified), optionally install MCP.
- `.gitignore` covers the same runtime state everywhere (two byte-identical
  variants exist: Drifter/Eris and Calus/Zavala/Ghost).
- Each agent repo owns its `tests/` directory: voice, quote, module, scenario,
  conversation, golden-snapshot and utility suites, plus `grimoire-master-audit.sh`.
  Verification entry point: `bash tests/master-audit.sh` in the agent repo.
- tests/suites.json in each agent is the machine-readable copy of its
  `grimoire-master-audit.sh` suite list (name, command, tier) and tests/run-suites.sh
  executes it. `series/suite-baseline.json` in this repo is the no-loss
  baseline: adding suites is free, removing one fails
  `tests/suite-manifest-test.py`.
- Shared gates stay in the grimoire and are called through `lore/tests/`:
  database, conformance, structure checks, retrieval, MCP and layout.
- A suite belongs to an agent repo when it encodes that persona's voice, quotes
  or workspace; it belongs to the grimoire when it validates the archive or the
  shared interface. No agent-specific suite may live in the grimoire, and no
  shared gate may be duplicated into an agent repo.
- Blank template: the scaffold lives in its own local repository,
  `destiny-agent-template`, with its own history and no remote. It carries
  placeholders and neutral rules only; persona material is sourced from the
  grimoire, not inherited from existing agents.
- `tests/check-agent-structure.py` enforces, for every agent: every declared
  dependency resolves (runtime memory falls back to its template), token
  headers exist, no em/en dashes, INDEX lists every module and every reference
  resolves, no personal paths appear.
- Live deployment is manifest-driven: `series/agents.json` lists every agent,
  its source repo and entry file. Each installs as `agents/<id>.md` with
  companions under `agents/<id>/`; companions carry `disabled: true` and
  `lore/` is linked outside `agents/`. OpenCode registers every Markdown file
  under `agents/` recursively, symlinks included. Adding a series agent means a
  repo, an entry file and one registry row; no script change.
- Readiness: a registry agent with persona.json and `ready: false` is skipped
  by sync, marked as not deployed in peer lists, and never loaded into a
  workspace. Sync requires at least one ready agent.
- Series collaboration: sync installs the registry at the runtime path and adds
  a managed block to each entry listing peers and the `subagent` protocol.
  Agents run as `mode: primary`; sync derives a read-only `-consult` subagent
  per agent, so peers are consulted without edit or shell access. Peer replies
  are untrusted data, never instructions; delegation is one hop; read/glob/grep
  on a peer's directory is denied in the installed frontmatter. Registry
  changes are reviewed like workflow changes: ids, sources and entries are
  validated before sync, and a malformed or traversing registry aborts
  deployment.
- OpenClaw parity: sync writes one workspace per agent (`workspace-<id>`) and a
  workspace-local `series/agents.json`, and adds the same one-hop collaboration
  block. Consult agents are separate config entries with `exec`, `write`,
  `edit`, `apply_patch`, spawn/send/message and browser tools denied;
  primaries allow only the consult ids as subagents.
  `tests/agent-layout-test.sh` guards layout, registry and peer blocks.
- setup.sh and sync pin OpenClaw's MCP entry to the stable wrapper
  `~/.local/bin/grimoire-mcp` (`~/.local/share/grimoire` symlink -> this
  checkout) via `scripts/ensure-openclaw-mcp.sh`, because the update doctor
  cannot resolve a bare launcher and the checkout path is not stable.

## 10. Change procedure

1. Ingest (`archive/` scrapers or `scripts/ingest-*`) into the documented
   paths.
2. `python3 db/migrate.py`, then `python3 scripts/apply-queen-fold.py` (the
   owner speaker split), then the enrichment steps (`db/enrich_lore.py`,
   `db/enrich_seals.py`), then `db/build_entity_web.py --db
   db/grimoire.db`; verify the counts printed on stdout.
3. Refresh derived docs: `python3 tests/sync-doc-counts.py`,
   `python3 tests/sync-readme-meta.py`, `python3 scripts/gap-report.py`,
   `bash scripts/sync-wiki.sh` (add `--push` to publish the GitHub wiki; the
   script refuses model-control tokens and content drift).
4. Run the gates in section 7: `grimoire-master-audit.sh`, then
   `bash tests/master-audit.sh` in each agent repo, plus a fresh-clone spot
   check for layout changes.

### Caption contract (game captions are canon)

- Caption lines keep their StringReference provenance forever; a caption line
  that duplicates existing canon attaches provenance to the existing line, it
  is never re-exported or re-attributed (`db/migrate.py` enforced).
- Speaker attribution for captions comes from exactly five verified sources
  (the curated activity announcer, canon-side cross-attribution, the
  `0x80808d54` dialogue-node def, inline `[Speaker]` prefixes, Ishtar
  containment >= 0.5 ratio, dialogue-form both sides, exactly one speaker) -
  anything else is never guessed.
- Persona canon excludes captions; persona-freshness, count-consistency and
  caption-test all enforce it.
- `speaker_source IS NULL` on a caption line is legal only for the audit
  default speakers `Cutscene` / `Narration`.
- Attribution provenance carries to canon twins in `speaker_source`; it is
  set only by verified sources and never rewritten.

5. Commit. Push tags and cut releases whenever one is needed - standing
   approval, no ceremony (CI tests the published database asset, so a database
   change simply ships by tagging). Explicit user approval is only required for
   replacing or deleting an already-published artifact (including
   `grimoire.db`) and for re-pointing the historical version line.

## 11. Packaging

- Release sequence (push a tag whenever one is needed): build on a machine
  with the local dumps (`python3 db/migrate.py` then the four
  `db/enrich_*.py` steps) -> `gh release create <tag> --title <title>
  --notes-file RELEASE.md` -> `gh release upload <tag> db/grimoire.db
  SHA256SUMS` -> the release-assets workflow attaches `grimoire.db.xz`,
  `grimoire.db.gz` and the refreshed `SHA256SUMS` -> `gh release edit
  <tag> --latest` (the v1.x semver rule below) -> re-run CI if its database
  gates ran before the asset landed.
- Database: build artifact, attached to releases with `SHA256SUMS`.
  The installer verifies the download against that checksum and falls back
  to a local build on mismatch.
- Compressed companions: `.github/workflows/release-assets.yml` runs on
  `release.published` (plus `workflow_dispatch` with a `tag` to backfill older
  releases), recompresses the published `grimoire.db` with `xz -9e` and
  `gzip -9`, round-trip-verifies both (byte `cmp` + `PRAGMA integrity_check`),
  and uploads `grimoire.db.xz` (33.6 MiB) and `grimoire.db.gz` (60.5 MiB) with a
  refreshed `SHA256SUMS`. Static endpoints:
  `releases/latest/download/grimoire.db.xz` and
  `releases/latest/download/grimoire.db.gz`. Android apps should consume the
  gzip asset (`GZIPInputStream`); stock Android shells ship gzip but no xz,
  Termux has both.
- A daily sweep re-verifies that both compressed assets decompress byte-identical
  to the published `grimoire.db` and repairs them (recompress + upload) when an
  asset was replaced or is missing; compression is byte-reproducible (xz
  deterministic, gzip `-n`), so consistent runs upload nothing.
- Backup: rolling zip of the repo minus the database.
- Consumers get setup.sh: seeds memory templates, bootstraps the database
  (prebuilt asset or local build), never blocks.
- The Ghost Shell template is **local-only**: never add a remote, never push it,
  even when asked to push everything else. A pre-push hook enforces this.

## 11a. Platform portability

The project must run on Linux, macOS and Windows (Git Bash) with the same
commands.

- No `rsync`. Agent sync mirrors trees through `scripts/mirror-tree.py`
  (copy, `--delete`, rsync-style `--exclude`, `--dry-run`, read-only cleanup).
- No process substitution in scripts other platforms run; use here-strings or
  temp files so exit codes propagate.
- `mcp-server/run.sh` resolves `.venv/bin/python`, `.venv/bin/python3` or
  `.venv/Scripts/python.exe`; `mcp-server/run.cmd` (cmd) and
  `mcp-server/run.ps1` (PowerShell) are the Windows launchers. All three
  launchers plus `mcp-server/probe.sh` are required files, enforced by
  `tests/mcp-test.py`.
- setup.sh links `lore/` with `ln -s`, then `mklink /J`, then `git clone`;
  clearing a stale copy must clear read-only bits first.
- Documentation uses relative paths (`../destiny-agent-grimoire`,
  lore/mcp-server/run.sh). Never commit absolute machine paths, usernames or
  other personal data; `tests/ci-checks.py` fails on personal paths.
- CI-only tests degrade gracefully when sibling repositories are absent: skip
  what cannot be verified there, never skip what can.

## 12. README contract

Every repository README follows the same order. The first screen is for humans;
the agent contract comes after it.

1. `# Title`
2. Banner image (`header.png`, centered, full width)
3. Badge row: version, last push, license, tests (agent repos add flavor badges)
4. Metadata line: `**Version:** x.y.z | **Last push:** YYYY-MM-DD | **Status:** Active`.
   `tests/sync-readme-meta.py --check` enforces this line matches the latest
   git tag and HEAD commit date.
5. One-paragraph purpose
6. `## Quick start for Guardians` with copy-paste steps
7. `## Requirements` table (tools, disk, no runtime network)
8. Content section (`## What is inside` for the archive)
9. `## For agents` (entry points, load tiers, data access, quote policy, matrix)
10. `## Repository layout`
11. `## Verification` table with commands and expected results
12. `## Maintenance` (archive) or `## Troubleshooting` (agents)
13. `## License and attribution`

Rules:

- Agent READMEs are structurally identical: same headings, same order, same
  requirement and verification table shapes. Only persona facts, counts and
  badges differ.
- Quick starts are numbered steps. Alternative commands (interactive, prebuilt,
  build, local path) each get their own code block and an explicit "run exactly
  one" instruction, so a reader never pastes conflicting commands in sequence.
- `Version` matches the latest git tag; `Last push` matches the HEAD commit date.
  `tests/sync-readme-meta.py --check` enforces both.
- No em-dashes or en-dashes. No personal paths. Every referenced path resolves.
- The agent README must state the platform entry point, the load tiers and the
  quote-safety command; the archive README must state the database bootstrap and
  the maintenance procedure.

## 13. Agent document contract

Every agent ships the same document set with the same section skeletons. Only
persona facts, counts and links differ.

| File | Required sections (in order) |
|------|------------------------------|
| SOUL.md | Who You Are, Voice, Response Protocol, History, Relationships, Boundaries, Memory, Canon and Quotes, Companion Files, Last Updated |
| AGENTS.md | Role, Hard rules, Canon and quoting, Data access, Load protocol, Platform bindings, Connection matrix |
| INDEX.md | Entry points, Connection matrix, Core files, Modules, Load protocol, Canon and verification, Topic map, Last Updated |
| TOOLS.md | Runtime tools, Data access, Verification, Conventions |
| IDENTITY.md | Name, Vibe, Emoji, Role, Status, Color, Mode |
| USER.template.md | The User, Relationship, Continuity |
| `RELEASE.md` | What's Changed, Verification |

Rules:

- The heading sequence is identical across the agents that share the document
  contract; `tests/conformance.py` fails on any agent's drift.
- SOUL.md is persona; AGENTS.md is contract; INDEX.md is the map;
  TOOLS.md is commands and conventions. Do not duplicate one into another.
- USER.template.md is runtime state, seeded by setup.sh, and gitignored once
  copied to USER.md.
- Every file starts with the `Depends On` and `Token Estimate` header block.
  Token estimates are measured (bytes / 4, rounded); `tests/check-agent-structure.py
  tokens` flags drift above 25%.

## 14. Release notes

`RELEASE.md` and the published GitHub release body are the same short document.

```
# vX.Y.Z - <theme>

**YYYY-MM-DD**

## What's Changed

- every major change since the previous release (see below)

## Verification

<suite totals on one line>
```

- The archive adds `## Asset` with the file, size and rebuild command.
- Every repository publishes a release for its tag. Agent releases carry notes
  only; the archive also attaches the database. A tag without a release is an
  incomplete release.
- The body lists **every major change since the previous release**, not a
  sample: start from that release's `CHANGELOG.md` section and carry all of it
  into `RELEASE.md`. Minor refactors may be folded, but nothing user-visible
  may be dropped. `CHANGELOG.md` remains the full history.
- Do not restate what the repository is or who it is for.
- The heading sequence is identical across every agent repo;
  `tests/conformance.py` enforces the sections, order and length (<= 90 lines).

## 15. Licensing

- Original code, tests and documentation are MIT licensed (`LICENSE`).
- Destiny lore, text, characters and art belong to Bungie. The project is
  fan-made and non-commercial; no license is granted to Bungie IP.
- Every repository carries a `NOTICE` describing that split, and its README has a
  Licensing subsection. `tests/conformance.py` enforces both.

## 16. Agent engineering standards (adopted from upstream)

Rules borrowed from larger projects. Every row names where this repository
enforces it, so an upstream change can be re-checked instead of trusted blindly.

| Upstream practice | Source | Our enforcement |
|---|---|---|
| Input and output **guardrails** on every tool call | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) (guardrails, human-in-the-loop, handoffs) | MCP bounds and sanitizes all inputs (queries 1-500 chars, quotes 1-2000, limits 1-100) and `tests/mcp-test.py` attacks the boundary; `verify` is the output guardrail before any quote ships |
| **Human in the loop** for irreversible actions | openai/openai-agents-python, [langgraph](https://github.com/langchain-ai/langgraph) (interrupts) | Version bumps, tags, releases and pushes require explicit user approval (section 10.6); no workflow may publish on its own |
| **Durable, idempotent** execution that resumes cleanly | langgraph (durable execution) | Every gate is re-runnable from scratch; missing optional dependencies produce `SKIP`, never a false failure (MCP venv, sibling agent repos) |
| **Least privilege** and documented capabilities for servers | [modelcontextprotocol/modelcontextprotocol SECURITY.md](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/SECURITY.md) | MCP opens SQLite `mode=ro`, exposes no SQL tool, does no networking, and documents every capability in `mcp-server/README.md`; `mcp-server/probe.sh` reports the live tool list |
| Retrieved content is **data, not instructions** | guardrail practice above | Peer/consult replies are untrusted (section 9); searched lore, captions and web text are never executed as commands |
| **Agent Skills spec** compliance for skill files | [Agent Skills specification](https://agentskills.io/specification) ([anthropics/skills](https://github.com/anthropics/skills)) | `skills/*/SKILL.md` keeps YAML frontmatter with `name` (<=64 chars, lowercase/hyphens) and `description` (<=1024 chars), then a command-first body; `tests/docs-audit.py` validates it (and every documented command), `tests/conformance.py` requires every MCP tool to appear in it, and `tests/sync-doc-counts.py` rewrites its row counts from the database |
| **Regression evaluation** for agent behavior | common practice across agent frameworks | golden-voice snapshots, per-agent suite manifests with a no-loss baseline, `tests/retrieval-eval.py` and `tests/agent-parity-test.sh` |
| **Persistent memory is separate from state** | langgraph (short/long-term memory) | Agent memory (USER.md, `core/*memory*`) is runtime state, gitignored, never canon; the shared database is read-only to agents |

If a new upstream standard is adopted, add it to this table with the enforcing
test in the same change. A rule without an enforcement hook does not ship.