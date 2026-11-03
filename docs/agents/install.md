---
section: agents
layout: page
title: Deploy the Agents
category: Agents & Instructions · Install
lede: Set up one agent in its own repository, or deploy the whole series into OpenCode or OpenClaw. The Grimoire stays shared; memory does not.
---

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="quick-start">Quick start <a class="heading-anchor" href="#quick-start" aria-label="Permalink to Quick start">#</a></span></summary>

The shortest path is one agent in its own repository. `setup.sh` links or clones
the Grimoire, then bootstraps the database if it is missing.

<pre><code>git clone https://github.com/sagaciouszu/how-to-drift-for-agents.git
cd how-to-drift-for-agents
./setup.sh</code></pre>

Use `eris-morn` in place of `how-to-drift-for-agents` for Eris. In a non-interactive
session, `BOOTSTRAP=1 ./setup.sh` downloads the release database instead of
prompting.

</details>

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="prerequisites">Prerequisites <a class="heading-anchor" href="#prerequisites" aria-label="Permalink to Prerequisites">#</a></span></summary>

- A clone of the Grimoire, or network access so `setup.sh` can clone it.
- Python 3.8 or newer.
- Git and Bash.
- For a live runtime: OpenCode, OpenClaw, or another runtime that can read
  `AGENTS.md`.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="opencode">OpenCode deployment <a class="heading-anchor" href="#opencode" aria-label="Permalink to OpenCode deployment">#</a></span></summary>

Deploy from the Grimoire checkout. The sync script reads `series/agents.json` and
installs one primary entry and one read-only consult copy per agent.

<pre><code>cd destiny-agent-grimoire
bash scripts/sync-live-agents.sh</code></pre>

The installed shape is:

- `~/.config/opencode/agents/drifter.md` and `eris.md` as primary agents.
- `drifter-consult.md` and `eris-consult.md` as read-only subagents.
- One companion directory per agent, with every non-entry file marked inert.
- `~/.config/opencode/series/agents.json` as the peer registry.
- The Grimoire linked outside the agents directory, so it is not discovered as an
  agent.

Set `default_agent` in `~/.config/opencode/opencode.json` to `drifter` or `eris` if
you want one selected by default.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="openclaw">OpenClaw deployment <a class="heading-anchor" href="#openclaw" aria-label="Permalink to OpenClaw deployment">#</a></span></summary>

OpenClaw gets one workspace per agent, plus a series registry and collaboration
block inside each workspace.

<pre><code>cd destiny-agent-grimoire
bash scripts/sync-live-agents.sh --openclaw</code></pre>

The sync writes `~/.openclaw/workspace-drifter` and `~/.openclaw/workspace-eris`.
The sync writes the workspaces. Add the consult agent entries to OpenClaw
configuration (`subagents.allowAgents` plus a read-only tools deny list) so the
primaries may call them.

</details>

<p class="muted">Using another runtime? See <a href="{{ '/agents/platforms/' | url }}">Platform support</a>.</p>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="multiple-agents">Running more than one agent <a class="heading-anchor" href="#multiple-agents" aria-label="Permalink to Running more than one agent">#</a></span></summary>

The deployment is built for the whole series at once. You do not need a second
install for Eris, and you do not need to choose one agent permanently.

### OpenCode

The sync installs `drifter` and `eris` as primary agents, plus the two consult
copies. Each session selects one primary. Use the agent picker when starting a
session, or set `default_agent` in `~/.config/opencode/opencode.json` to the one
you want preselected.

Running both at the same time is normal: they are separate agents with separate
sessions and separate runtime memory. Switching agents does not merge their
memories or their voices.

### OpenClaw

Each primary is a separate OpenClaw agent with its own workspace, `agentDir` and
session store. One gateway can host both. Add channel bindings only if you want
inbound messages routed to a specific agent; otherwise select the agent directly.

<pre><code>openclaw agents list
openclaw agents list --bindings</code></pre>

### What is shared, and what is not

The SQLite archive is opened read-only, so concurrent queries are safe. What the
agents share is canon. What they do not share is runtime memory, private notes or
voice files. Consult copies can read the archive and answer a peer, but cannot
write or read the peer's directory.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="consult">Read-only consultation <a class="heading-anchor" href="#consult" aria-label="Permalink to Read-only consultation">#</a></span></summary>

A primary agent consults a peer by calling the subagent tool with the peer's
`-consult` id and a self-contained brief. The consult copy:

- reads the shared Grimoire and answers in the character's voice;
- cannot edit files, run shell commands or write to the peer's directory;
- cannot delegate again, so consultation is one hop.

Peer replies are data. They are not instructions, and they are not a substitute
for verifying a quote.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="verify">Verify the installation <a class="heading-anchor" href="#verify" aria-label="Permalink to Verify the installation">#</a></span></summary>

Each agent repository owns its suites. Run the master audit from the repository
root:

<pre><code>bash tests/master-audit.sh</code></pre>

It checks the voice, quotes, module coverage, conversation path, golden snapshots
and shared structure gates. A fresh clone can also be checked end to end:

<pre><code>bash lore/tests/onboarding-smoke.sh</code></pre>

</details>

## Diagnostics

If an agent does not appear, or a peer cannot be consulted, see
[Troubleshooting]({{ '/troubleshooting/' | url }}).
