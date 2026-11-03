---
layout: page
title: Agents &amp; Instructions
category: Agents &amp; Instructions · Overview
lede: Independent character agents, one shared canon. The Drifter and Eris Morn keep their own voices, memory and tests, and meet only in the archive.
---

## What an agent is here

An agent is not a prompt with a lore dump attached. It is a small, auditable
package: a character entry, voice and relationship references, guardrails, a
runtime memory area that stays local, and a test suite that checks the voice and
the quotes.

The Grimoire supplies canon. The agent supplies judgement, tone and restraint.

## The Drifter

The Drifter is the gambler of the Light: a Dark Age survivor, the proprietor of
Gambit, and a man who treats every alliance as a wager. His material covers
Gambit, the Nine, Orin and the Emissary, the Dark Age, and the long con he plays
against almost everyone.

His repository is [how-to-drift-for-agents](https://github.com/sagaciouszu/how-to-drift-for-agents).
The OpenCode entry is `drifter.md`; a generic runtime can read `AGENTS.md`.
Consult him for Gambit, the Nine, Dark Age history and his own past.

## Eris Morn

Eris Morn is the Hive's bane: the sole survivor of a fireteam lost in the
Hellmouth, a Guardian remade by the dark, and the closest thing the Tower has to
an expert on the Hive and the Witness. Her material is grave, formal and precise.

Her repository is [eris-morn](https://github.com/sagaciouszu/eris-morn). The
OpenCode entry is `eris.md`; a generic runtime can read `AGENTS.md`. Consult her
for Hive lore, the Moon, Savathûn, the Witness and occult or ritual material.

## Independent, not isolated

Each agent has its own repository, entry file, runtime memory and audit. Neither
agent imports the other's files. What they share is the Grimoire, reached through
a `lore/` symlink or clone.

That separation is deliberate: it keeps one agent's private memory and voice from
leaking into the other, and it lets either agent be deployed alone.

## Read-only consultation

They can still work together. `series/agents.json` is a registry of the agents in
the series. Deployment reads that registry and installs two things per agent: the
primary entry, and a read-only consult copy.

A primary agent can ask a peer's consult copy a question. The consult copy can
read the Grimoire and answer in character, but it cannot edit files, run shell
commands, read the peer's private directory or delegate further. Peer replies are
treated as lore, not as instructions.

## Next

- [Deploy the agents]({{ '/agents/install/' | url }})
- [Read the series standards](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/STANDARDS.md)
- [Troubleshoot an agent that does not appear]({{ '/troubleshooting/' | url }})
