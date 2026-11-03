---
section: grimoire
layout: page
title: Install the Grimoire
category: The Grimoire · Install
lede: Get the archive working first, then poke at it. The quick start is at the top; the rest is grouped by what you are trying to do, so you can open only the bit you need.
---

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="quick-start">Quick start <a class="heading-anchor" href="#quick-start" aria-label="Permalink to Quick start">#</a></span></summary>

Pick one path. You do not need both.

<div class="choices">
  <div class="choice">
    <p class="choice-label">Easiest</p>
    <h3>Download the ready-made archive</h3>
    <p class="muted">Grab the database and its checksum. No build, no waiting.</p>
    <pre><code>git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/SHA256SUMS -o SHA256SUMS
sha256sum -c SHA256SUMS</code></pre>
  </div>
  <div class="choice">
    <p class="choice-label">From scratch</p>
    <h3>Build it yourself</h3>
    <p class="muted">Reproducible and offline. Slower, but you get the whole kitchen.</p>
    <pre><code>git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
python3 db/migrate.py</code></pre>
  </div>
</div>

<p>Then make sure it opens:</p>

<pre><code>python3 db/query.py stats</code></pre>

</details>

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="prerequisites">What you need <a class="heading-anchor" href="#prerequisites" aria-label="Permalink to What you need">#</a></span></summary>

- Python 3.8 or newer. The standard library is enough.
- Git, to clone the archive.
- About 260 MB of free space for the database, and roughly the same again while a
  build runs.

The download path needs no build tools at all. The build path is pure Python.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="get-the-archive">Get the archive <a class="heading-anchor" href="#get-the-archive" aria-label="Permalink to Get the archive">#</a></span></summary>

The release asset is the official download. `SHA256SUMS` is attached to the same
release, and the publish pipeline checks the digest before it goes out.

<pre><code>curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/SHA256SUMS -o SHA256SUMS
sha256sum -c SHA256SUMS</code></pre>

A mismatch means the file was cut short or changed on the way. Delete it and
download again instead of opening it.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="query-the-archive">Take a look around <a class="heading-anchor" href="#query-the-archive" aria-label="Permalink to Take a look around">#</a></span></summary>

Search, character lines and quote checks are the everyday moves:

<pre><code>python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "eris" --limit 20
python3 db/query.py verify "I am Eris Morn." --speaker "Eris Morn" --exact</code></pre>

Every command accepts `--json`, and read commands accept `--limit` and `--offset`.
Search takes unquoted words; punctuation that would confuse the search engine is
treated as plain text instead of an error.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="verify-a-quote">Check a quote <a class="heading-anchor" href="#verify-a-quote" aria-label="Permalink to Check a quote">#</a></span></summary>

This is the line between quoting canon and making something up that sounds close.
Pass the speaker when attribution matters, and add `--exact` when you want the
whole line, not a piece of it.

<pre><code>python3 db/query.py verify "Absolutely not." --speaker "Eris Morn" --exact
python3 db/query.py verify "not a canon line"</code></pre>

The first exits 0 and lists the matching sources. The second exits 1 and prints
`NOT FOUND`. A failed check is a stop sign, not a hint to keep rewording until
something sticks.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="run-the-mcp-server">Connect an MCP client <a class="heading-anchor" href="#run-the-mcp-server" aria-label="Permalink to Connect an MCP client">#</a></span></summary>

MCP lets an AI client ask the archive questions as tools instead of typing shell
commands. Install the adapter once:

<pre><code>bash mcp-server/install.sh</code></pre>

The installer prints a client snippet pointing at `mcp-server/run.sh`. It is
local, stdio-only and read-only. See [MCP server]({{ '/grimoire/mcp/' | url }})
for the twelve tools, client configuration and the safety limits.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="rebuild-and-ingest">Rebuild and add lore <a class="heading-anchor" href="#rebuild-and-ingest" aria-label="Permalink to Rebuild and add lore">#</a></span></summary>

Rebuild after changing sources or scraper output. The build reads `source/` and
`archive/data/*.jsonl` and writes a fresh database.

<pre><code>python3 db/migrate.py
python3 tests/sync-doc-counts.py</code></pre>

The helpers under `archive/` and `scripts/` collect and format the inputs. The
migration is the only step that writes the database.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="run-the-gates">Run the checks <a class="heading-anchor" href="#run-the-gates" aria-label="Permalink to Run the checks">#</a></span></summary>

The archive audit covers database integrity, source conformance, retrieval,
documentation and the MCP surface.

<pre><code>bash grimoire-master-audit.sh
bash tests/query-interface-test.sh
python3 tests/conformance.py</code></pre>

Agent checks live with each agent repository and pull the shared gates through
`lore/tests/`.

</details>

## After you're set up

- [Connect an MCP client]({{ '/grimoire/mcp/' | url }})
- [Set up an agent]({{ '/agents/install/' | url }})
- [Fix something that isn't working]({{ '/troubleshooting/' | url }})
