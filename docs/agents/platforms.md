---
section: agents
layout: page
title: Platform Support
category: Agents & Instructions · Platforms
lede: OpenCode and OpenClaw are script-managed. Everything else uses the generic agent contract, which is just files and an optional MCP connection.
---

## The generic contract

An agent repository is portable. It contains an entry file, `AGENTS.md`,
`INDEX.md`, `TOOLS.md`, voice and world references, guardrails and `setup.sh`.
The runtime supplies the model, the conversation and the tools; the repository
supplies the character and the canon connection.

OpenCode and OpenClaw get first-class deployment because the sync script knows
their layouts. Other runtimes read the same files without an adapter.

## Runtimes that read AGENTS.md

Clone the agent repository, run `setup.sh`, and load `AGENTS.md` as the agent's
standing instructions. Runtimes that support an `AGENTS.md` convention, or any
tool that can load a Markdown instruction file, need no adapter.

<pre><code>git clone https://github.com/sagaciouszu/how-to-drift-for-agents.git
cd how-to-drift-for-agents
./setup.sh</code></pre>

Use `INDEX.md` as the map, `TOOLS.md` for the query surface, and the agent's
`core/`, `voice/`, `world/` and `reference/` directories as the deep material.
The `lore/` link supplies the archive. Keep the runtime's working directory at
the repository root, or set `WORKSPACE` to it.

## MCP-capable clients

The persona and the canon are separate concerns. Load `AGENTS.md` for the voice,
then register the Grimoire MCP server for the tools:

<pre><code>bash lore/mcp-server/install.sh</code></pre>

The server is local stdio and read-only. A client that only accepts remote MCP
servers needs a local bridge; a client with shell access can start
`lore/mcp-server/run.sh` directly. The installer prints the exact path.

## Skill-based runtimes

If the runtime loads skill files, point it at
`lore/skills/destiny-grimoire/SKILL.md`. The skill describes the query commands
and the quote policy without requiring MCP.

## Runtimes with no filesystem access

You can still paste `AGENTS.md` and the relevant `core/` files as a system
prompt, but the agent loses canon queries and quote verification. Treat that as a
degraded deployment and do not present guesses as verified lore.

## What sync does not do

The deployment script does not install into arbitrary runtimes, write another
platform's configuration, or copy credentials. Those bindings stay deliberately
manual.

## Next

- [Deploy into OpenCode or OpenClaw]({{ '/agents/install/' | url }})
- [Troubleshoot a missing agent or tool]({{ '/troubleshooting/' | url }})
