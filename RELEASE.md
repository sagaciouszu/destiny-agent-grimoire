# v0.24.0 - Authoritative releases and Destiny 1 coverage

**2026-11-04**

## What's Changed

- **Authoritative transcript releases:** every Ishtar web transcript now carries
  the page's `Added In` release (1,130/1,130), captured by
  `archive/data/fetch_transcript_releases.py`. Classification no longer guesses
  from recording dates.
- **Transcript classification:** explicit 104 -> 1,234, unknown 389 -> 1, and
  transcripts with no expansion 1,115 -> 1.
- **Destiny 1 surfaced:** 0 -> 120 transcripts and 1,418 dialogue lines across
  Destiny, The Dark Below, House of Wolves, The Taken King and Rise of Iron.
- **Scraped footer cleanup:** contributor credits and related-content labels are
  no longer ingested as narration. Canon lines 73,012 -> 67,472.
- **Item sets:** 19 curated manifest sets classify 555 more items; item
  `unknown` 10,068 -> 9,513.
- **Gap ledger:** `docs/GAPS.md` now reports transcript and dialogue coverage by
  game, alongside activities, events and sparse speakers.
- **Regression gate:** a cross-check fails if any Ishtar web transcript lacks
  release metadata.

## Verification

9/9 archive suites, 89/89 query interface, 51/51 database, 14/14 taxonomy,
11/11 source cross-check, conformance PASS.

## Asset

`grimoire.db` with authoritative transcript releases, Destiny 1 coverage,
clean canon lines and item-set classification. SHA256 in `SHA256SUMS`.
