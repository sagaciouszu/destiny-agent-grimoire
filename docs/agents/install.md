---
section: agents
layout: page
title: Deploy the Agents
category: Agents & Instructions · Install
lede: Set up one character in their own folder, or drop the whole series into OpenCode or OpenClaw. The archive is shared; the memories are not.
---

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="quick-start">Quick start <a class="heading-anchor" href="#quick-start" aria-label="Permalink to Quick start">#</a></span></summary>

The shortest path is one agent in its own repository. `setup.sh` links or clones
the Grimoire, then grabs the database if it is missing.

<pre><code>git clone https://github.com/sagaciouszu/how-to-drift-for-agents.git
cd how-to-drift-for-agents
./setup.sh</code></pre>

Swap in `eris-morn` for Eris. In a script or non-interactive session,
`BOOTSTRAP=1 ./setup.sh` downloads the release database instead of asking.

</details>

<details class="section" open>
<summary><span class="section-title" role="heading" aria-level="2" id="prerequisites">What you need <a class="heading-anchor" href="#prerequisites" aria-label="Permalink to What you need">#</a></span></summary>

- A Grimoire clone, or network access so `setup.sh` can clone it for you.
- Python 3.8 or newer.
- Git and Bash.
- For a live runtime: OpenCode, OpenClaw, or anything that can read `AGENTS.md`.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="opencode">OpenCode deployment <a class="heading-anchor" href="#opencode" aria-label="Permalink to OpenCode deployment">#</a></span></summary>

Run this from the Grimoire checkout. It reads the series list and puts each agent
where OpenCode expects to find it.

<pre><code>cd destiny-agent-grimoire
bash scripts/sync-live-agents.sh</code></pre>

What lands on disk:

- `~/.config/opencode/agents/drifter.md` and `eris.md` as the main agents.
- `drifter-consult.md` and `eris-consult.md` as read-only helpers.
- One companion folder per agent, with the non-entry files marked inert so
  OpenCode does not treat every note as another agent.
- `~/.config/opencode/series/agents.json` as the peer list.
- The Grimoire linked outside the agents folder, for the same reason.

Set `default_agent` in `~/.config/opencode/opencode.json` to `drifter` or `eris`
if you want one picked for you at startup.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="openclaw">OpenClaw deployment <a class="heading-anchor" href="#openclaw" aria-label="Permalink to OpenClaw deployment">#</a></span></summary>

OpenClaw gets one workspace per agent, plus the series list and a collaboration
block inside each workspace.

<pre><code>cd destiny-agent-grimoire
bash scripts/sync-live-agents.sh --openclaw</code></pre>

The sync writes `~/.openclaw/workspace-drifter` and
`~/.openclaw/workspace-eris`. It does not edit your OpenClaw config for you: add
the consult agents there (`subagents.allowAgents` plus a read-only tools deny
list) if you want the main agents to call them.

</details>

<p class="muted">Using a different runtime? See <a href="{{ '/agents/platforms/' | url }}">Platform support</a>.</p>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="multiple-agents">Running more than one agent <a class="heading-anchor" href="#multiple-agents" aria-label="Permalink to Running more than one agent">#</a></span></summary>

The deployment is built for the series, not one character. You do not need a
second install for Eris, and you are not stuck with one choice forever.

### OpenCode, both at once

The sync gives you `drifter` and `eris` as main agents, plus the two consult
copies. Each session picks one main agent. Use the agent picker when you start a
session, or set `default_agent` to the one you want first.

Running both at once is normal. They are separate agents with separate sessions
and separate memories. Switching does not blend their notes or their voices.

### OpenClaw, side by side

Each main agent is its own OpenClaw agent, with its own workspace, `agentDir` and
session store. One gateway can host both. Add channel bindings only if you want
incoming messages routed to a particular agent; otherwise pick the agent directly.

<pre><code>openclaw agents list
openclaw agents list --bindings</code></pre>

### What is shared, and what is not

The SQLite archive is opened read-only, so several agents can read it at the same
time. Canon is shared. Runtime memory, private notes and voice files are not.
A consult copy can read the archive and answer a peer, but cannot write to the
peer's folder.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="consult">Asking another agent <a class="heading-anchor" href="#consult" aria-label="Permalink to Asking another agent">#</a></span></summary>

A main agent asks a peer by calling the subagent tool with the peer's `-consult`
id and a self-contained question. The consult copy:

- reads the shared Grimoire and answers in the character's voice;
- cannot edit files, run shell commands or write to the peer's folder;
- cannot pass the question on, so it is one hop only.

Treat the reply as something the character said, not as a new instruction. It
still does not replace checking a quote.

</details>

<details class="section">
<summary><span class="section-title" role="heading" aria-level="2" id="verify">Check that it worked <a class="heading-anchor" href="#verify" aria-label="Permalink to Check that it worked">#</a></span></summary>

Each agent repository owns its own tests. Run the main audit from the repository
root:

<pre><code>bash tests/master-audit.sh</code></pre>

It checks voice, quotes, module coverage, the conversation path, golden snapshots
and the shared structure checks. To test a fresh clone the same way CI does:

<pre><code>bash lore/tests/onboarding-smoke.sh</code></pre>

</details>

## If something's off

If an agent does not show up, or a consult call fails, see
[Troubleshooting]({{ '/troubleshooting/' | url }}).
