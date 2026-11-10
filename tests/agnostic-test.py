#!/usr/bin/env python3
"""Agnostic contract: shared executables never hardcode an agent repository.

`series/agents.json` is the roster. Every shared script that needs an agent
repository reads it (directly or through `tests/_roster.py`). A literal
`destiny-agent-<persona>` in a shared executable means a new agent would be
silently skipped, so this gate fails on one unless the line carries an
explicit `# agnostic-allow: <reason>` marker.

CI workflow files are excluded: GitHub Actions checks out a concrete repository
as a link fixture, which is an operational choice, not a roster default.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "_site"}
SCAN = ("tests", "scripts", "db", "mcp-server", "skills")
SUFFIXES = (".py", ".sh", ".yml", ".yaml")


def sources():
    """Agent repository names, read from the registry (never written here)."""
    manifest = os.path.join(ROOT, "series", "agents.json")
    if not os.path.isfile(manifest):
        return []
    import json
    with open(manifest, encoding="utf-8") as fh:
        return [row["source"] for row in json.load(fh).get("agents", [])
                if row.get("source")]


def files():
    for top in SCAN:
        base = os.path.join(ROOT, top)
        if not os.path.isdir(base):
            continue
        for current, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in names:
                if name.endswith(SUFFIXES):
                    yield os.path.join(current, name)


def main():
    names = sources()
    if not names:
        print("SKIP: series/agents.json has no agent sources")
        return 0
    pattern = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b")
    issues = []
    scanned = 0
    for path in files():
        scanned += 1
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for number, line in enumerate(fh, 1):
                if "agnostic-allow:" in line:
                    continue
                for match in pattern.finditer(line):
                    issues.append((os.path.relpath(path, ROOT), number, match.group(0)))
    print(f"shared executables scanned: {scanned}")
    if issues:
        for path, number, name in issues:
            print(f"  {path}:{number} hardcodes {name}")
        print(f"ISSUES: {len(issues)}")
        return 1
    print("PASS: shared executables read the registry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
