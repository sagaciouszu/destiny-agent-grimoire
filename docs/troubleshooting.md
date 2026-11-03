---
layout: page
title: Troubleshooting
category: Diagnostics
lede: Start from the symptom. Each entry names the cause, the check and the fix, and links back to the relevant install page.
---

<nav class="toc" aria-labelledby="toc-title">
<p class="toc-title" id="toc-title">On this page</p>
<ul>
  <li><a href="#database-missing">The database is missing</a></li>
  <li><a href="#checksum">The checksum does not match</a></li>
  <li><a href="#lore-link">The lore link is dangling</a></li>
  <li><a href="#mcp-tools">MCP tools do not appear</a></li>
  <li><a href="#agent-missing">An agent is not listed</a></li>
  <li><a href="#consult">A peer cannot be consulted</a></li>
  <li><a href="#verify">A quote does not verify</a></li>
  <li><a href="#tests">Tests fail after cloning</a></li>
</ul>
</nav>

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="database-missing">The Grimoire database is missing <a class="heading-anchor" href="#database-missing" aria-label="Permalink to The Grimoire database is missing">#</a></span></summary>

Symptoms: every query fails with `database not found`, or the agent reports
degraded canon access.

The database is a build artifact and is not committed. Download the release asset
or build it:

<pre><code>curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
python3 db/migrate.py</code></pre>

Run one of them, not both. If a previous download left a partial file, delete
`db/grimoire.db` first.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="checksum">The release checksum does not match <a class="heading-anchor" href="#checksum" aria-label="Permalink to The release checksum does not match">#</a></span></summary>

The download was incomplete or altered. Delete the database and download it
again; do not open or migrate a file that failed the check.

<pre><code>rm -f db/grimoire.db
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
sha256sum -c SHA256SUMS</code></pre>

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="lore-link">The lore link is dangling <a class="heading-anchor" href="#lore-link" aria-label="Permalink to The lore link is dangling">#</a></span></summary>

An agent repository expects `lore/` to point at a Grimoire checkout or to be a
clone of it. If the link was moved, recreate it:

<pre><code>./setup.sh /path/to/destiny-agent-grimoire</code></pre>

`setup.sh` removes a dangling link and recreates it. Do not place the Grimoire
inside the OpenCode agents directory; it would be discovered as thousands of
agents.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="mcp-tools">The MCP client shows no Grimoire tools <a class="heading-anchor" href="#mcp-tools" aria-label="Permalink to The MCP client shows no Grimoire tools">#</a></span></summary>

Install the adapter, then register the path it prints:

<pre><code>bash mcp-server/install.sh</code></pre>

The client must start `mcp-server/run.sh`, not `server.py`. Use the absolute path
when the client does not inherit the repository working directory. The server is
stdio-only; a URL-based client cannot connect to it.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="agent-missing">OpenCode does not list the agent <a class="heading-anchor" href="#agent-missing" aria-label="Permalink to OpenCode does not list the agent">#</a></span></summary>

Re-run the sync and confirm the installed files:

<pre><code>cd destiny-agent-grimoire
bash scripts/sync-live-agents.sh</code></pre>

Expected entries are `drifter.md`, `eris.md`, `drifter-consult.md` and
`eris-consult.md` under `~/.config/opencode/agents/`. Companion files must be
inert, and the Grimoire must live outside that directory.

If the agent exists but is not selectable, check `default_agent` in
`~/.config/opencode/opencode.json` and use the exact id, without the file
extension.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="consult">A peer cannot be consulted <a class="heading-anchor" href="#consult" aria-label="Permalink to A peer cannot be consulted">#</a></span></summary>

Consultation targets the peer's `-consult` entry, not the primary. Primary agents
are `primary`-only and cannot run as subagents.

Check that the registry lists both agents and that the consult entries were
installed. Consult copies are read-only by design: they cannot run shell commands
or delegate further. That is expected, not a fault.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="verify">A quote does not verify <a class="heading-anchor" href="#verify" aria-label="Permalink to A quote does not verify">#</a></span></summary>

`verify` is exact about what it accepts. Common causes:

- The line is a paraphrase. Rephrase it as your own words, or find the canonical
  line.
- The speaker is wrong or too vague. Pass the full speaker name and add `--exact`.
- The text contains hidden formatting characters. They are stripped before
  comparison, but copied text can still differ from the source line.
- The database is stale. Rebuild and retry.

Do not quote a line that fails verification.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="tests">Tests fail immediately after cloning an agent <a class="heading-anchor" href="#tests" aria-label="Permalink to Tests fail immediately after cloning an agent">#</a></span></summary>

A fresh clone has no runtime memory files. Run onboarding before the audit:

<pre><code>./setup.sh --no-mcp "$PWD/lore"
bash tests/master-audit.sh</code></pre>

The same sequence is used by CI. If the audit still fails, run the reported suite
directly; each suite prints the specific missing file or mismatched count.

</details>
