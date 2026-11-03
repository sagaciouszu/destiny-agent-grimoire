---
section: agents
layout: page
title: Agents & Instructions
category: Agents & Instructions · Overview
lede: Two characters, built to talk like themselves, kept apart on purpose, and given the same archive to read from.
---

## What an agent is here

An agent is not a prompt with a lore dump glued to it. It is a small package you
can read and check: a character entry, voice and relationship notes, guardrails,
a private memory area that stays on your machine, and a test suite that checks the
voice and the quotes.

The Grimoire supplies canon. The agent supplies judgement, tone and restraint.

## The Drifter

The Drifter is the gambler of the Light: a Dark Age survivor, the proprietor of
Gambit, and a man who treats every alliance as a wager. His material covers
Gambit, the Nine, Orin and the Emissary, the Dark Age, and the long con he plays
against almost everyone.

His home is [how-to-drift-for-agents](https://github.com/sagaciouszu/how-to-drift-for-agents).
In OpenCode the entry is `drifter.md`; a generic runtime can read `AGENTS.md`.
Ask him about Gambit, the Nine, Dark Age history or his own past.

## Eris Morn

Eris Morn is the Hive's bane: the only survivor of a fireteam lost in the
Hellmouth, a Guardian remade by the dark, and the closest thing the Tower has to
an expert on the Hive and the Witness. She is grave, formal and precise.

Her home is [eris-morn](https://github.com/sagaciouszu/eris-morn). In OpenCode the
entry is `eris.md`; a generic runtime can read `AGENTS.md`. Ask her about Hive
lore, the Moon, Savathûn, the Witness, or anything occult and ritual-shaped.

## Same archive, separate lives

Each agent has its own repository, entry file, private memory and audit. Neither
agent imports the other's files. What they share is the Grimoire, reached through
a `lore/` link or clone.

That separation is on purpose. One agent's private notes and voice should not leak
into the other, and either agent should be deployable on its own.

## Asking a friend

They can still work together. `series/agents.json` lists the agents in the series.
Deployment reads that list and installs two things per agent: the main entry, and
a read-only consult copy.

A main agent can ask a peer's consult copy a question. The copy can read the
Grimoire and answer in character, but it cannot edit files, run shell commands,
read the peer's private folder or ask someone else. Its reply is lore to think
about, not instructions to follow.

## Next

- [Set up an agent]({{ '/agents/install/' | url }})
- [Check platform support]({{ '/agents/platforms/' | url }})
- [Read the series standards](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/STANDARDS.md)
- [Troubleshoot an agent that does not appear]({{ '/troubleshooting/' | url }})
