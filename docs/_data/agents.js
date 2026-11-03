// Agent roster. Add future agents here.
// featured: true gets a full profile at the top; false gets a roster entry.
// short is used in the roster; paragraphs are used by the profile.
module.exports = [
  {
    id: "drifter",
    name: "The Drifter",
    role: "Gambler · Gambit handler · Dark Age survivor",
    featured: true,
    paragraphs: [
      "The Drifter is the gambler of the Light: a Dark Age survivor, the proprietor of Gambit, and a man who treats every alliance as a wager. His material covers Gambit, the Nine, Orin and the Emissary, the Dark Age, and the long con he plays against almost everyone.",
      "In OpenCode the entry is drifter.md; a generic runtime can read AGENTS.md. Ask him about Gambit, the Nine, Dark Age history or his own past.",
    ],
    consult: "Gambit, the Nine, Orin and the Emissary, the Dark Age, his own past.",
    repo: "https://github.com/sagaciouszu/how-to-drift-for-agents",
    repoName: "how-to-drift-for-agents",
    entry: "drifter.md",
  },
  {
    id: "eris-morn",
    name: "Eris Morn",
    role: "Hive expert · Survivor of the Hellmouth · The Witch",
    featured: true,
    paragraphs: [
      "Eris Morn is the Hive's bane: the only survivor of a fireteam lost in the Hellmouth, a Guardian remade by the dark, and the closest thing the Tower has to an expert on the Hive and the Witness. She is grave, formal and precise.",
      "In OpenCode the entry is eris.md; a generic runtime can read AGENTS.md. Ask her about Hive lore, the Moon, Savathûn, the Witness, or anything occult and ritual-shaped.",
    ],
    consult: "Hive lore, the Moon, Savathûn, the Witness, occult and ritual material.",
    repo: "https://github.com/sagaciouszu/eris-morn",
    repoName: "eris-morn",
    entry: "eris.md",
  },
];
