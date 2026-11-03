# v1.6.0 - MCP reading tools and pagination

**2026-11-03**

## What's Changed

- **MCP reading tools:** `book`, `transcript`, `find_item` and `record` join search, character, item, verify and listings for ten tools total
- **Pagination:** every list-like tool and CLI command accepts `offset`; books and transcripts report totals
- **Resources:** `grimoire://books`, `grimoire://characters`, `grimoire://records` and `grimoire://stats` for discovery
- **Tool metadata:** read-only/idempotent annotations on every tool; limits and text caps unchanged
- **CLI parity:** `book`, `transcript`, `find-item`, `record` and `--offset` on search, character and list
- **Tests:** interface 27 checks, MCP matrix 138 calls across ten tools and four resources

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 37/37 database, 27/27 interface, 6/6 MCP, extended 5/5 groups, conformance PASS.

## Asset

`grimoire.db` is unchanged (164 MB, sha256 `285e31e6cd5415f7a5d92b15ffde9cb41d0c260df2fc451fba838f9b10a401e9`). `SHA256SUMS` is attached.
