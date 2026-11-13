# Legacy archive index

Local repository hygiene performed 2026-11-13. Current corpus inputs and active
build tools remain in place; this index records only superseded assets and
where retained history can be found.

| Item | Disposition / pointer |
|---|---|
| Seven retired one-off scripts | Retained under `archive/legacy/scripts/`; see `scripts/README.md` for replacements and rationale. |
| `site-split` branch | Branch removed after preserving its complete history in `archive/legacy/branches/site-split.bundle`. Restore with `git fetch archive/legacy/branches/site-split.bundle refs/heads/site-split:refs/heads/site-split`. |
| Pre-0.19.0 releases (`v0.4.1`–`v1.8.1`) | All 15 directories, including their historical database assets, moved intact to `../../releases/archive/old-releases/`. This is a local archive outside this Git repository. |
| Five `captions.jsonl.*.bak` files | Removed as obsolete recovery copies; `archive/data/captions.jsonl` is the canonical caption source. |
| `archive/data/containment-verification.jsonl` | Removed generated ledger; its former generator is retained in `scripts/verify-containment.py`, and containment behavior is exercised by `tests/containment-test.py`. |
| Archived search repository | Already retained at sibling `destiny-agent-grimoire-search/`; Pagefind is the active site search. See the workspace README. |
| `backup/captions-reconcile-2026-11-08` and site `backup/hallmark-redesign` branches | Retained as backup refs; they were not deleted or rewritten. |
| `archive/data/transcripts_overlap.jsonl` | Intentionally retained: `tests/source-overlap-verify.py` reads it as test input. |

The other scripts listed as archive candidates in the 2026-11-13 legacy audit
remain in `scripts/` where live-build orchestration, audit gates, enrichment,
or current documentation still references them.
