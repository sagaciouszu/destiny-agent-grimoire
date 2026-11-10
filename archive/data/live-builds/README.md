# Per-build live caption tiers

`scripts/refresh-live-build.py` writes a new build's combined English tier here
as `<build-id>.jsonl`. Records carry `source_build` and build-scoped slugs, so
they coexist with the current build's `archive/data/captions-live.jsonl`.

`db/migrate.py` loads this directory after the current file. A changed line in a
later build is a new `caption_sightings` row, never an inline rewrite of an
earlier build's text.
