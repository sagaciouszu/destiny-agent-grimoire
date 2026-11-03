---
section: agents
layout: page
title: Platform Support
category: Agents & Instructions · Platforms
lede: OpenCode and OpenClaw get a one-command setup. Anything else can still use the same files, with a little manual wiring.
---

## The basic idea

An agent repository is portable. It contains an entry file, `AGENTS.md`,
`INDEX.md`, `TOOLS.md`, voice and world notes, guardrails and `setup.sh`. Your
runtime supplies the model, the conversation and the tools. The repository
supplies the character and the link to canon.

OpenCode and OpenClaw get first-class treatment because the sync script knows
their folders. Other runtimes read the same files; there is no special build.

## Runtimes that read AGENTS.md

Clone the agent repository, run `setup.sh`, and load `AGENTS.md` as the standing
instructions. If the runtime understands an `AGENTS.md` file, or can load a
Markdown instruction file, you are done.

<pre><code>git clone https://github.com/sagaciouszu/how-to-drift-for-agents.git
cd how-to-drift-for-agents
./setup.sh</code></pre>

`INDEX.md` is the map, `TOOLS.md` is the query surface, and `core/`, `voice/`,
`world/` and `reference/` hold the deep material. The `lore/` link supplies the
archive. Keep the working directory at the repository root, or set `WORKSPACE` to
that path.

## MCP-capable clients

The character and the archive are separate jobs. Load `AGENTS.md` for the voice,
then point the client at the Grimoire MCP server for canon:

<pre><code>bash lore/mcp-server/install.sh</code></pre>

The server is local stdio and read-only. A client that only accepts remote
servers needs a small local bridge; a client that can start a process can run
`lore/mcp-server/run.sh` directly. The installer prints the exact path.

## Skill-based runtimes

If the runtime loads skill files, point it at
`lore/skills/destiny-grimoire/SKILL.md`. The skill explains the query commands
and the quote policy without needing MCP.

## Runtimes with no file access

You can paste `AGENTS.md` and the relevant `core/` files into a system prompt, but
the agent then has no canon lookup and no quote checking. Treat that as a limited
setup, and do not present guesses as verified lore.

## What sync does not do

The deployment script does not install into arbitrary runtimes, edit another
platform's configuration, or copy credentials. Those bindings are deliberately
left in your hands.

## Next

- [Deploy into OpenCode or OpenClaw]({{ '/agents/install/' | url }})
- [Troubleshoot a missing agent or tool]({{ '/troubleshooting/' | url }})
