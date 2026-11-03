---
layout: page
title: Install the Grimoire
category: The Grimoire · Install
lede: Get a working archive first, then query it, verify against it and connect an agent. Start with the shortest path and open the other sections only when you need them.
---

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="quick-start">Quick start <a class="heading-anchor" href="#quick-start" aria-label="Permalink to Quick start">#</a></span></summary>

<div class="choices">
  <div class="choice">
    <p class="choice-label">Recommended</p>
    <h3>Use the release database</h3>
    <p class="muted">Fastest. Downloads the prebuilt archive and its checksum.</p>
    <pre><code>git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/SHA256SUMS -o SHA256SUMS
sha256sum -c SHA256SUMS</code></pre>
  </div>
  <div class="choice">
    <p class="choice-label">From source</p>
    <h3>Build the database</h3>
    <p class="muted">Reproducible, offline, and slower. Reads the committed sources.</p>
    <pre><code>git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
python3 db/migrate.py</code></pre>
  </div>
</div>

<p>Confirm the archive is readable:</p>

<pre><code>python3 db/query.py stats</code></pre>

</details>

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="prerequisites">Prerequisites <a class="heading-anchor" href="#prerequisites" aria-label="Permalink to Prerequisites">#</a></span></summary>

- Python 3.8 or newer, standard library only.
- Git, to clone the archive.
- About 260 MB of disk for the database, or the same again while a build runs.

The release path needs no build tooling. The source path runs entirely on the
Python standard library.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="get-the-archive">Get the archive <a class="heading-anchor" href="#get-the-archive" aria-label="Permalink to Get the archive">#</a></span></summary>

The release asset is the canonical download. `SHA256SUMS` is attached to the same
release, and the build pipeline checks the digest before publishing.

<pre><code>curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/SHA256SUMS -o SHA256SUMS
sha256sum -c SHA256SUMS</code></pre>

A checksum mismatch means the download was incomplete or altered. Delete the
database and repeat the download rather than opening it.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="query-the-archive">Query the archive <a class="heading-anchor" href="#query-the-archive" aria-label="Permalink to Query the archive">#</a></span></summary>

Search, character lines and verification are the common paths:

<pre><code>python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "eris" --limit 20
python3 db/query.py verify "I am Eris Morn." --speaker "Eris Morn" --exact</code></pre>

Every command accepts `--json`, and read commands accept `--limit` and `--offset`.
Search accepts unquoted multi-word input; punctuation that is not valid FTS5 syntax
is treated literally.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="verify-a-quote">Verify a quote <a class="heading-anchor" href="#verify-a-quote" aria-label="Permalink to Verify a quote">#</a></span></summary>

Verification is the boundary between quoting canon and paraphrasing it. Pass the
speaker when attribution matters, and add `--exact` when the whole line is being
quoted.

<pre><code>python3 db/query.py verify "Absolutely not." --speaker "Eris Morn" --exact
python3 db/query.py verify "not a canon line"</code></pre>

The first command exits 0 and prints matching sources. The second exits 1 and
prints `NOT FOUND`. A failed check is a stop sign, not a suggestion to rephrase
until something matches.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="run-the-mcp-server">Run the MCP server <a class="heading-anchor" href="#run-the-mcp-server" aria-label="Permalink to Run the MCP server">#</a></span></summary>

The MCP adapter lets a client use the archive as typed tools instead of shell
commands. Install its virtual environment once:

<pre><code>bash mcp-server/install.sh</code></pre>

The installer prints a client configuration snippet pointing at
`mcp-server/run.sh`. The server is stdio-only, read-only, and clamps limits and
output size. It exposes search, character, item, verify, book, transcript, record,
list, stats and batch verification tools.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="rebuild-and-ingest">Rebuild and ingest <a class="heading-anchor" href="#rebuild-and-ingest" aria-label="Permalink to Rebuild and ingest">#</a></span></summary>

Rebuild after changing sources or scraper output. The build reads
`source/` and `archive/data/*.jsonl` and rewrites the database.

<pre><code>python3 db/migrate.py
python3 tests/sync-doc-counts.py</code></pre>

Ingestion helpers live under `archive/` and `scripts/`. They write the JSONL and
markdown inputs; the migration is the only step that writes the database.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="run-the-gates">Run the gates <a class="heading-anchor" href="#run-the-gates" aria-label="Permalink to Run the gates">#</a></span></summary>

The archive audit covers database integrity, source conformance, retrieval,
documentation and the MCP surface.

<pre><code>bash grimoire-master-audit.sh
bash tests/query-interface-test.sh
python3 tests/conformance.py</code></pre>

The agent audit lives with each agent repository and calls the shared gates
through `lore/tests/`.

</details>

## Diagnostics

If the database is missing, the MCP client shows no tools, or verification
behaves unexpectedly, see [Troubleshooting]({{ '/troubleshooting/' | url }}).
