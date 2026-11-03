# {{name}} - Tools

> **Depends On:** AGENTS.md
> **Token Estimate:** ~0.6K tokens

## Query CLI

- Query CLI: one of `python3 lore/db/query.py search|character|character-info|item|book|transcript|find-item|record|verify|verify-many|list|stats`; MCP tool names use underscores.
- Search: `python3 lore/db/query.py search "<term>" --limit 10`
- Character lines: `python3 lore/db/query.py character "{{name}}" --limit 20`
- Quote check: `python3 lore/db/query.py verify "<line>" --speaker "{{name}}" --exact`
- Stats: `python3 lore/db/query.py stats`

## MCP (optional)

Twelve tools over stdio: `search`, `character`, `item`, `verify`,
`list_records`, `stats`, `book`, `transcript`, `find_item`, `record`,
`verify_many`, `character_info`. Register `lore/mcp-server/run.sh`.

## Verification

- Full audit: `bash tests/master-audit.sh`
- Module checks: `bash tests/module-test.sh`
- Quotes: `bash tests/quote-verify.sh`
- Database integrity: `bash lore/tests/test-db.sh` (38 checks)
