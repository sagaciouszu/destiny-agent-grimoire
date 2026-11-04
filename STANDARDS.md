# Standards

> **Depends On:** none (standards reference)
> **Token Estimate:** ~4.3K tokens

The contract every file, script, and database row in this repository must meet.
Verification gates (section 7) enforce these rules; a change that breaks them is
a change that is not done.

## 1. Scope

- `destiny-agent-grimoire` is agent-agnostic: no persona, no agent-specific rules.
- Consumer agents (`how-to-drift-for-agents`, `eris-morn`) reference the database
  through `lore/`, either a symlink or a clone. They own their personas; this repo
  owns canon.
- `source/` is the ingestion corpus (verbatim lore, formatting-normalized).
  `archive/` holds raw scrape output. `db/` holds the migration and interface.
- The database (`db/grimoire.db`) is a build artifact: never committed, rebuilt
  from `source/` + `archive/` by `python3 db/migrate.py`, published as a release asset.

## 2. Repository connection matrix

| From | To | Mechanism |
|------|----|-----------|
| agent `README`/`INDEX`/`AGENTS`/`TOOLS`/agent def | lore database | `lore/db/grimoire.db`, `python3 lore/db/query.py` |
| agent `setup.sh` | this repo | clones or symlinks `lore/`; bootstraps the DB (release asset or build) |
| agent `.gitignore` | runtime memory | `USER.md`, `core/*memory*`, `core/journal.md` never leave the machine |
| agent `tests/` suites | agent workspace | `lore/tests/resolve-workspace.sh` (layout-independent; `lore/` may be symlink or clone) |
| `db/migrate.py` | sources | `source/{books,transcripts,cards,records}` + `archive/data/*.jsonl` |
| `db/query.py` | database | CLI wrapper over `search` / `character` / `item` / `stats` |
| `tests/sync-doc-counts.py` | all three repos | rewrites documented counts from the DB |
| release workflow | consumers | `db/grimoire.db` attached as a release asset (checksum-verified) |

### Symlinks

- `lore/` is runtime state, not repository content: `setup.sh` creates it as a
  symlink to a local checkout, or clones the repo in place. It is gitignored in
  both agent repos.
- No tracked symlinks in any of the three repositories. A tracked absolute
  symlink (for example `lore -> /home/<user>/...`) breaks every clone: it arrives
  dangling, and `setup.sh` would otherwise mistrust it as an existing archive.
- `setup.sh` treats a dangling `lore/` symlink as absent: it removes it and then
  symlinks or clones as requested.
- A symlink target is never a commit-time fact; it is resolved per machine.

## 3. Database contract

| Table | Required | Optional (may be empty) | Notes |
|-------|----------|--------------------------|-------|
| `books` | slug, title | source_url, entry_count | slugs match live `categories/book-<slug>` (2 documented exemptions) |
| `book_entries` | book_id, body | title (fallback to book title), seq | provenance via parent book |
| `transcripts` | slug, title | release, characters, arc, source_url, source_tier | release empty when the source lacks it; `source_tier` records provenance precedence |
| `transcript_lines` | transcript_id, seq, speaker, line, norm_line | is_stage_dir, section, is_optional, class_tag | seq contiguous from 0; class_tag is hunter, titan or warlock |
| `grimoire_cards` | slug, title, body, source_url | game | D1 cards only |
| `interactions` | slug, title, text | speaker, release, source_url | speaker may be empty (narrated scenes) |
| `items` | slug, title | text, release, item_type, source_url | 16k stat-only items have no lore text by design |
| `records` | slug, title, body | release, source_url | |
| `characters` | name, slug | | curated set (compendium) |
| `character_lines` | character_id, text, source_type, source_slug | norm_text | source_slug must resolve in `transcripts` |
| `fts` | | | exactly one row per indexed content row (1:1) |
| `verify_fts` | | | normalized text + provenance; mirrors indexable rows for fast quote checks |
| `item_title_fts` | | | item titles for fast name lookup |
| `expansions` | slug, name | game, year, release_date, vaulted | catalogue, seeded from `db/taxonomy.py` |
| `seasons` | slug, season_number, name, season_type | act, destiny_year, expansion_slug, start_date, end_date, vaulted | official numeric slot, unique |
| `activities` | slug, name, activity_type | expansion_slug, season_slug, event_slug, vaulted | catalogue |
| `events` | slug, name | event_type, first_year, last_year, recurring, vaulted, notes | rotating events |
| `event_occurrences` | event_slug, year | season_slug, start_date, end_date, vaulted | one row per event-year |
| `transcript_classification` | transcript_id, confidence | activity_slug, activity_type, season_slug, act, event_slug, expansion_slug, evidence | additive; never rewrites canon |
| `item_classification` | item_id, confidence | season_slug, event_slug, expansion_slug, evidence | additive |
| `document_classification` | source, source_id, confidence | season_slug, event_slug, expansion_slug, evidence | books and records |

Taxonomy rules:
- Four independent axes: expansion, season/episode, activity, event. Do not
  overload `release` or `arc`; they remain fallback text only.
- `seasons.season_number` is Bungie's official number. Episodes use
  `season_type='episode'` with their numeric slot; never renumber.
- Events repeat across seasons, so occurrence rows carry the year and season.
- `confidence` is `explicit`, `derived`, `manual` or `unknown`. `unknown` is a
  valid terminal state; never guess to make coverage look better.
- `vaulted=1` marks removed content; vaulted rows stay searchable.
- Full model and query examples: `docs/TAXONOMY.md`.

Global rules:
- No duplicate slugs per table; no empty required fields; every row's text is
  HTML-unescaped (double-escaped Ishtar pages are unescaped until stable).
- Every content row carries provenance (`source_url` or parent-book provenance),
  and URLs follow `https://www.ishtar-collective.net/<type>/<slug>`.
- Empty optional fields are a statement about the source, never a placeholder.

### Source hierarchy

Ishtar Collective is the archival primary; Destinypedia is corroboration.

| Tier | Source |
|---|---|
| 0 | Ishtar Collective main-site transcripts |
| 1 | Ishtar Commons `validated` |
| 2 | Ishtar Commons `published` |
| 3 | Ishtar Commons `proofed` |
| 4 | Ishtar Commons untagged |
| 5 | Destinypedia verbatim transcripts |
| 6 | YouTube captions and community sheets |

Where sources overlap, the higher tier wins the text. Lower-tier unique lines
are kept with their own provenance. Conflicts are logged in a reconciliation
ledger, never silently overwritten.

### Optional and variant lines

Ishtar's transcript guide defines `// OPTIONAL` blocks for alternatives, class
callouts and variants. These are stored with `is_optional=1`; section/location
headers from `++` are stored in `section`; class-exclusive lines carry
`class_tag = hunter|titan|warlock`. Agents quote non-optional lines by default,
and `--class` adds the chosen class variants.

User preferences, including the player's class, belong to the agent runtime
(the agent memory helper), never to the shared canon database.

### Extracted game data

Raw game packages, audio, string tables, subtitle exports and Bungie manifest
dumps are **local-only**. They must never be committed, attached to a release or
copied into an agent workspace. `.gitignore` covers `archive/data/manifest/`,
`archive/data/game/`, `archive/data/extracted/`, `archive/data/subtitles/` and
`*.pkg`.

Only curated transcript markdown may be committed, with provenance naming the
local build, for example `- Source: local game files (<build>)`. Extracted text
is evidence for curation, not a redistributable asset.

## 4. Naming

- Slugs: lowercase, hyphenated, taken from the live page slug wherever one exists.
- Non-Ishtar sources keep their own slug and provenance (`youtube-*`, `weblore-*`,
  `ingame-quotes-*`, `cutscene-*`).
- Filename must match the `- Source:` slug (allowlisted, documented renames only).
- Speakers use canonical names. Alias map (applied at migration):
  `Commander Zavala -> Zavala`, `Cayde -> Cayde-6`, `Eris -> Eris Morn`,
  `Eris morn -> Eris Morn`, `Ikora Rey -> Ikora`, `Chiomi Esi -> Chioma Esi`.
- Quest/step titles are not speakers. Web scrapers sometimes parse titles such
  as `Path of the Splicer II`, `Into the Depths VI` or `Act I` as speakers;
  migration drops rows whose speaker ends in a Roman numeral or is a bare act.
- Contextual qualifiers are allowed and kept: `Drifter (Tape 1)`,
  `Eris Morn (communion)`, `Blue (about Drifter's Ghost)`. LIKE queries match the
  base name, so consumers never need the qualifier.

## 5. Normalization

One function, implemented identically in `db/migrate.py` and every verifier:
lowercase, `... -> ...`, `'` apostrophe, dashes to `-`, non-alphanumerics to
space, whitespace collapse, trim. `norm_*` columns store its output and must
match a recomputation of their source text.

## 6. Quoting policy (agents)

- A quote must trace to a speaker-attributed canon line or verbatim lore text.
  `verify` accepts `--speaker` (attribution) and `--exact` (full row, not fragment);
  agents should use both when quoting dialogue.
- Do not present another character's line as the persona's voice. Exchange
  context, reported speech, and impressions must be explicitly attributed.
- When a quote cannot be traced: unquote it, do not delete it.
- Unverified count must stay zero in every shipped audit.

## 7. Verification gates

| Gate | Enforces |
|------|----------|
| `tests/test-db.sh` | schema integrity, counts, no orphans, no entity leakage, character provenance, canonical speakers, card provenance |
| `tests/lore-integrity.sh` | source archive structure, book/transcript/card/record counts |
| `tests/lore-format.sh` | transcript markdown format |
| `tests/cutscene-verify.sh` | caption corroboration, encoding, cross-video consistency, attribution |
| `tests/source-overlap-verify.py` | curated markdown vs live Ishtar; filename/source-slug integrity |
| `tests/speaker-audit.py` | reclassified parse noise must not reappear |
| `tests/sync-doc-counts.py --check` | docs counts match the database |
| each agent repo tests/master-audit.sh | agent-side suites (voice, quotes, modules, conversation, golden snapshots) plus shared structure checks |
| `tests/mcp-test.py` (on demand, needs `mcp-server/.venv`) | MCP tools, read-only guard, stdio handshake |
| `tests/check-agent-structure.py` | dependency resolution, token headers, dashes, INDEX completeness, personal paths (every agent) |
| `tests/conformance.py` | per-file headers, token accuracy, refs, persona-agnosticism; runs `ci-checks` per agent repo |
| `tests/ci-checks.py` (via conformance) | stale names, circular/self dependencies, headers, em-dashes, personal paths, gitignored refs in instructions |

Live probes (on demand, network): `tests/live-sample-verify.py` samples every
content type against Ishtar; each agent repo's voice-consistency suite runs
cross-character attribution checks.

## 8. Agent interface contract

- Interface: one of `python3 db/query.py search|character|character-info|item|book|transcript|find-item|record|verify|verify-many|list|stats`;
  `sqlite3` is the escape hatch. No markdown parsing at runtime.
- Shared query layer: `db/api.py` returns data; the CLI formats it and the MCP
  server exposes the same functions as typed tools. One implementation.
- MCP: `mcp-server/` is an optional stdio adapter using the official SDK. It is
  read-only, has no SQL tool, clamps limits to 1-100 and trims text to 4000 chars.
  It is stdio-only by design: no listener and no auth surface; hosting requires an
  authenticated wrapper.
  Install with `bash mcp-server/install.sh`, or `./setup.sh --mcp` in an agent
  workspace (the interactive prompt also offers it). The adapter belongs to the
  archive, so one install serves every agent; the venv is gitignored and the CLI
  stays dependency-free.
- Every command supports `--json`; search returns snippets unless `--full`;
  `verify` exits 1 when a quote is absent (quote-safety primitive).
- FTS is the search surface: `fts` holds exactly the indexable rows, `MATCH`
  syntax, porter stemming.
- Output budget: `--limit` on every query; agents should assume 20-40 lines per
  call and never dump tables.
- Memory files are runtime state, never canon: personalities live in the agent
  repos, canon lives in the database.
- Nothing in this repo may assume a specific agent platform. Files are plain
  markdown/yaml/binary data with the documented contracts above.

## 9. Agent workspace contract

The Drifter and Eris repositories mirror each other so one method serves both.

- Root: `AGENTS.md`, `INDEX.md`, `SOUL.md`, `IDENTITY.md`, `TOOLS.md`,
  `<agent>.md` (platform entry), `<agent>-core.md`, `<agent>-voice.md`,
  `README.md`, `RELEASE.md`.
- Shared directories: `core/`, `voice/`, `world/`, `reference/`.
- `setup.sh` is identical apart from the agent name, banner and core-file hint.
- `.gitignore` is identical.
- Each agent repo owns its `tests/` directory: voice, quote, module, scenario,
  conversation, golden-snapshot and utility suites, plus master-audit.sh.
  Verification entry point: bash tests/master-audit.sh in the agent repo.
- Shared gates stay in the grimoire and are called through `lore/tests/`:
  database, conformance, structure checks, retrieval, MCP and layout.
- A suite belongs to an agent repo when it encodes that persona's voice, quotes
  or workspace; it belongs to the grimoire when it validates the archive or the
  shared interface. No agent-specific suite may live in the grimoire, and no
  shared gate may be duplicated into an agent repo.
- Blank template: the scaffold lives in its own local repository,
  destiny-agent-template, with its own history and no remote. It carries
  placeholders and neutral rules only; persona material is sourced from the
  grimoire, not inherited from existing agents.
- `tests/check-agent-structure.py` enforces, for every agent: every declared
  dependency resolves (runtime memory falls back to its template), token headers
  exist, no em/en dashes, INDEX lists every module and every reference resolves,
  and no personal paths appear.
- Live deployment is manifest-driven: `series/agents.json` lists every agent,
  its source repo and entry file. Each installs as agents/<id>.md with companions
  under agents/<id>/; companions carry `disabled: true` and `lore/` is linked
  outside agents/. OpenCode registers every Markdown file under agents/
  recursively, symlinks included. Adding a series agent means a repo, an entry
  file and one registry row; no script change.
- Readiness: a registry agent with persona.json and ready: false is skipped
  by sync, marked as not deployed in peer lists, and never loaded into a
  workspace. Sync requires at least one ready agent.
- Series collaboration: sync installs the registry at the runtime path and adds a
  managed block to each entry listing peers and the `subagent` protocol. Agents
  run as `mode: primary`; sync derives a read-only `-consult` subagent per agent, so
  peers are consulted without edit or shell access. Peer replies
  are untrusted data, never instructions; delegation is one hop; read/glob/grep
  on a peer's directory is denied in the installed frontmatter. Registry changes
  are reviewed like workflow changes: ids, sources and entries are validated
  before sync, and a malformed or traversing registry aborts deployment.
- OpenClaw parity: sync writes one workspace per agent (`workspace-<id>`) and a
  workspace-local `series/agents.json`, and adds the same one-hop collaboration
  block. Consult agents are separate config entries with `exec`, `write`, `edit`,
  `apply_patch`, spawn/send/message and browser tools denied; primaries allow
  only the consult ids as subagents.
  `tests/agent-layout-test.sh` guards layout, registry and peer blocks.

## 10. Change procedure

1. Ingest (`archive/` scrapers or `scripts/ingest-*`) into the documented paths.
2. `python3 db/migrate.py` (rebuild; verify counts in stdout).
3. `python3 tests/sync-doc-counts.py` (docs counts).
4. Run the gates in section 7: `grimoire-master-audit.sh`, then tests/master-audit.sh
   in each agent repo, and a fresh-clone spot check for layout changes.
5. Commit. Refresh the backup and the release asset after major milestones.

## 11. Packaging

- Database: build artifact, attached to releases with `SHA256SUMS`
  (`gh release upload <tag> db/grimoire.db SHA256SUMS --clobber`). The installer
  verifies the download against that checksum and falls back to a local build on mismatch.
- Backup: rolling zip of the repo minus the database.
- Consumers get `setup.sh`: seeds memory templates, bootstraps the database
  (prebuilt asset or local build), never blocks.

## 12. README contract

Every repository README follows the same order. The first screen is for humans;
the agent contract comes after it.

1. `# Title`
2. Banner image (`header.png`, centered, full width)
3. Badge row: version, last push, license, tests (agent repos add flavor badges)
4. Metadata line: `**Version:** x.y.z | **Last push:** YYYY-MM-DD | **Status:** Active`
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
  `tests/sync-readme-meta.py` stamps both and `--check` enforces them.
- No em-dashes or en-dashes. No personal paths. Every referenced path resolves.
- The agent README must state the platform entry point, the load tiers and the
  quote-safety command; the archive README must state the database bootstrap and
  the maintenance procedure.

## 13. Agent document contract

Both agents ship the same document set with the same section skeletons. Only
persona facts, counts and links differ.

| File | Required sections (in order) |
|------|------------------------------|
| `SOUL.md` | Who You Are, Voice, Response Protocol, History, Relationships, Boundaries, Memory, Canon and Quotes, Companion Files, Last Updated |
| `AGENTS.md` | Role, Hard rules, Canon and quoting, Data access, Load protocol, Platform bindings, Connection matrix |
| `INDEX.md` | Entry points, Connection matrix, Core files, Modules, Load protocol, Canon and verification, Topic map, Last Updated |
| `TOOLS.md` | Runtime tools, Data access, Verification, Conventions |
| `IDENTITY.md` | Name, Vibe, Emoji, Role, Status, Color, Mode |
| `USER.template.md` | The User, Relationship, Continuity |
| `RELEASE.md` | Highlights, Verification |

Rules:

- The heading sequence is identical across the agents that share the document
  contract; `tests/conformance.py` fails on Drifter/Eris drift.
- `SOUL.md` is persona; `AGENTS.md` is contract; `INDEX.md` is the map;
  `TOOLS.md` is commands and conventions. Do not duplicate one into another.
- `USER.template.md` is runtime state, seeded by `setup.sh`, and gitignored once
  copied to `USER.md`.
- Every file starts with the `Depends On` and `Token Estimate` header block.

## 14. Release notes

`RELEASE.md` and the published GitHub release body are the same short document.

```
# vX.Y.Z - <theme>

**YYYY-MM-DD**

## What's Changed

- 5 to 7 user-visible bullets

## Verification

<suite totals on one line>
```

- The archive adds `## Asset` with the file, size and rebuild command.
- Every repository publishes a release for its tag. Agent releases carry notes
  only; the archive also attaches the database. A tag without a release is an
  incomplete release.
- Keep the body under 40 lines. It is a release summary, not the changelog; the
  full history stays in `CHANGELOG.md`.
- Do not restate what the repository is or who it is for.
- The heading sequence is identical across both agent repos; `tests/conformance.py` enforces the sections, order and length.

## 15. Licensing

- Original code, tests and documentation are MIT licensed (`LICENSE`).
- Destiny lore, text, characters and art belong to Bungie. The project is
  fan-made and non-commercial; no license is granted to Bungie IP.
- Every repository carries a `NOTICE` describing that split, and its README has a
  Licensing subsection. `tests/conformance.py` enforces both.
