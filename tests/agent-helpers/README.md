# Shared agent helpers (canonical copies)

These files are **intentionally byte-identical** in every agent repository under
`tests/` (and `memory.py` at the repository root). Agents are independent,
offline-capable repositories, so the helpers are distributed copies, not
symlinks. This directory is the canonical side of the guard.

| Canonical file | Distribution path | Purpose |
|---|---|---|
| `memory.py` | `memory.py` | local runtime memory CLI |
| `memory-test.py` | `tests/memory-test.py` | per-user memory isolation |
| `run-suites.sh` | `tests/run-suites.sh` | suite entry point |
| `suite-manifest-test.py` | `tests/suite-manifest-test.py` | suite loss/drift guard |
| `shared-helpers-test.sh` | `tests/shared-helpers-test.sh` | this guard |

The guard (`tests/shared-helpers-test.sh`) fails when a copy differs **or when a
canonical file is missing**. It does not silently skip missing files.

To change a helper: edit this directory, copy the file to all six agent repos and
to `destiny-agent-template/template/`, then run `bash tests/shared-helpers-test.sh`
in each. Update this table if the set changes.

Deliberately **not** shared: `setup.sh` (now identical by construction, not a
test helper), persona tests, fixtures, public keys, and Drifter/Eris custom
suites.
