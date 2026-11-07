# v0.29.0 - Schema 1.5.0: caption attribution provenance

**2026-11-07**

## What's Changed

Everything since v0.28.0:

- **Attribution provenance is stored, not dropped.** `transcript_lines`
  gains a nullable `speaker_source` recording how a caption line's speaker
  was attached: `ishtar_containment` (180 lines - a substantial fragment of a
  *spoken* canon line with exactly one speaker; the ratio guard rejects
  quotes misattributed inside long lore prose), `dialogue_node` (12 vendor
  lines FNV-1-verified in `0x80808d54` defs), `line_prefix` (2 inline
  `[Speaker]` lines). Twin lines already in canon adopt the tag only when
  their own field is empty; no attribution is ever rewritten. Schema 1.5.0;
  206 attributed caption lines carry provenance.
- **Docs.** Database.md's Game captions section now documents the
  exhaustive-SDH finding (zero additional attributable lines beyond the 180),
  the Tiger-engine literature audit, and the Ghost/Sagira companion-VO defs
  (24+24 name-keyed lines; text not obtainable statically - pkg 0x209 is not
  in this install). STANDARDS.md records the column; capabilities.json
  documents it.
- **Determinism.** Fresh double rebuild produces a byte-identical database
  dump (0-diff verified across consecutive rebuilds).

## Verification

Master audit 14/14; test-db 61/61; caption-test 9/9; count-consistency
21/21; taxonomy 17/17; query-interface 89/89; retrieval-eval ranked corpus
unchanged (P@5=0.96 / MRR=1.00); docs-audit 375 commands; sync-doc-counts in
sync; conformance clean; count-consistency 21/21.

## Asset

`grimoire.db` rebuilt from tracked sources plus local enrichment dumps;
companions `grimoire.db.xz` / `grimoire.db.gz` and refreshed `SHA256SUMS`
are attached by the release-assets workflow on publish.
