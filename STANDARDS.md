# Standards

> **Depends On:** none (standards reference)
> **Token Estimate:** ~1.7K tokens

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
| `tests/drifter-*`, `tests/eris-*` | agent workspace | `tests/resolve-workspace.sh` (layout-independent; `lore/` may be symlink or clone) |
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
| `transcripts` | slug, title | release, characters, arc, source_url | release empty when the source lacks it |
| `transcript_lines` | transcript_id, seq, speaker, line, norm_line | is_stage_dir | seq contiguous from 0 |
| `grimoire_cards` | slug, title, body, source_url | game | D1 cards only |
| `interactions` | slug, title, text | speaker, release, source_url | speaker may be empty (narrated scenes) |
| `items` | slug, title | text, release, item_type, source_url | 16k stat-only items have no lore text by design |
| `records` | slug, title, body | release, source_url | |
| `characters` | name, slug | | curated set (compendium) |
| `character_lines` | character_id, text, source_type, source_slug | norm_text | source_slug must resolve in `transcripts` |
| `fts` | | | exactly one row per indexed content row (1:1) |

Global rules:
- No duplicate slugs per table; no empty required fields; every row's text is
  HTML-unescaped (double-escaped Ishtar pages are unescaped until stable).
- Every content row carries provenance (`source_url` or parent-book provenance),
  and URLs follow `https://www.ishtar-collective.net/<type>/<slug>`.
- Empty optional fields are a statement about the source, never a placeholder.

## 4. Naming

- Slugs: lowercase, hyphenated, taken from the live page slug wherever one exists.
- Non-Ishtar sources keep their own slug and provenance (`youtube-*`, `weblore-*`,
  `ingame-quotes-*`, `cutscene-*`).
- Filename must match the `- Source:` slug (allowlisted, documented renames only).
- Speakers use canonical names. Alias map (applied at migration):
  `Commander Zavala -> Zavala`, `Cayde -> Cayde-6`, `Eris -> Eris Morn`,
  `Eris morn -> Eris Morn`, `Ikora Rey -> Ikora`, `Chiomi Esi -> Chioma Esi`.
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
| `drifter-master-audit.sh` / `eris-master-audit.sh` (shared `tests/agent-audit.sh`) | agent-side suites (voice, quotes, modules, dependency coverage, index completeness, hygiene) |
| `tests/conformance.py` | per-file headers, token accuracy, refs, persona-agnosticism; runs `ci-checks` per agent repo |
| `tests/ci-checks.py` (via conformance) | stale names, circular/self dependencies, headers, em-dashes, personal paths, gitignored refs in instructions |

Live probes (on demand, network): `tests/live-sample-verify.py` samples every
content type against Ishtar; `tests/drifter-voice-consistency.sh` /
`tests/eris-voice-consistency.sh` run cross-character attribution checks.

## 8. Agent interface contract

- Interface: `python3 db/query.py search|character|item|verify|list|stats`;
  `sqlite3` is the escape hatch. No markdown parsing at runtime.
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

## 9. Change procedure

1. Ingest (`archive/` scrapers or `scripts/ingest-*`) into the documented paths.
2. `python3 db/migrate.py` (rebuild; verify counts in stdout).
3. `python3 tests/sync-doc-counts.py` (docs counts).
4. Run the gates in section 7 (both agent audits + fresh-clone spot check for
   layout changes).
5. Commit. Refresh the backup and the release asset after major milestones.

## 10. Packaging

- Database: build artifact, attached to releases (`gh release upload <tag> db/grimoire.db --clobber`),
  digest verified against local sha256.
- Backup: rolling zip of the repo minus the database.
- Consumers get `setup.sh`: seeds memory templates, bootstraps the database
  (prebuilt asset or local build), never blocks.
