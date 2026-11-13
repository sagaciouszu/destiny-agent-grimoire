#!/usr/bin/env python3
"""Sync documented suite-check literals from the live suite scorecards.

Usage: python3 tests/gen-suite-counts.py [--check]
  --check reports drift without writing and exits 1 if any doc is stale.

CHANGELOG.md and RELEASE.md are intentionally exempt as historical records.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GRIMOIRE = os.path.dirname(HERE)
WORK = os.path.dirname(GRIMOIRE)
sys.path.insert(0, HERE)
import _roster
import suite_counts

AGENT_REPOS = _roster.repos()

# Map each suite to stable identifiers found on the same documentation line.
IDENTIFIERS = {
    "Database integrity": ("test-db.sh",),
    "Query interface": ("query-interface-test.sh",),
    "Agent layout": ("agent-layout-test.sh",),
    "Cutscene captions": ("cutscene-verify.sh",),
    "MCP contract": ("mcp-test.py",),
    "MCP agent optimisation": ("mcp-agent-optimization-test.py",),
}


def display_count(label, count):
    if count is None:
        return None
    if label == "MCP contract" or label == "Cutscene captions":
        return f"{count[0]}/{count[1]}"
    return str(count)


def collect_files():
    files = []
    for pattern in (
        os.path.join(GRIMOIRE, "*.md"),
        os.path.join(GRIMOIRE, "docs", "*.md"),
        os.path.join(GRIMOIRE, "docs", "process", "*.md"),
        os.path.join(GRIMOIRE, "docs", "wiki", "*.md"),
        os.path.join(GRIMOIRE, "skills", "destiny-grimoire", "*.md"),
        os.path.join(GRIMOIRE, "compendium", "*.md"),
    ):
        files.extend(glob.glob(pattern))
    for repo in AGENT_REPOS.values():
        if not os.path.isdir(repo):
            continue
        for subdir in ("", "reference", "core"):
            files.extend(glob.glob(os.path.join(repo, subdir, "*.md")))
    template = os.path.join(WORK, "destiny-agent-template")
    if os.path.isdir(template):
        for subdir in ("", "template"):
            files.extend(glob.glob(os.path.join(template, subdir, "*.md")))
    wiki = os.path.join(WORK, "destiny-agent-grimoire.wiki")
    if os.path.isdir(wiki):
        files.extend(glob.glob(os.path.join(wiki, "*.md")))
    site = os.path.join(WORK, "destiny-agent-grimoire-site")
    if os.path.isdir(site):
        for root, dirs, names in os.walk(site):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "_site")]
            files.extend(os.path.join(root, name) for name in names
                         if name.endswith((".md", ".njk")))
    # The master audit embeds counts in its suite labels too.
    files.append(os.path.join(GRIMOIRE, "grimoire-master-audit.sh"))
    return sorted({path for path in files if os.path.isfile(path)})


def sync_text(text, counts):
    out = []
    changed = False
    for line in text.splitlines(keepends=True):
        original = line
        if re.search(r"\bchecks\b", line, re.I):
            for label, identifiers in IDENTIFIERS.items():
                count = display_count(label, counts.get(label))
                if count is None or not any(token in line for token in identifiers):
                    continue
                # Replace the check-count token on this suite's line only;
                # preserve surrounding punctuation and singular/plural style.
                line = re.sub(r"\b\d+(?:/\d+)?(?=\s+checks\b)", count, line,
                              count=1, flags=re.I)
                break
        changed |= line != original
        out.append(line)
    return "".join(out), changed


def main():
    check_only = "--check" in sys.argv
    counts = suite_counts.suite_counts()
    files = collect_files()
    changes = []
    for path in files:
        if os.path.basename(path) in ("CHANGELOG.md", "RELEASE.md", "GRIMOIRE-CHANGES.md"):
            continue
        with open(path, encoding="utf-8") as stream:
            original = stream.read()
        updated, changed = sync_text(original, counts)
        if changed:
            changes.append(path)
            if not check_only:
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(updated)
    if changes:
        print(("WOULD UPDATE: " if check_only else "UPDATED: ") + str(len(changes)) + " files")
        for path in changes:
            print("  " + os.path.relpath(path, WORK))
        return 1 if check_only else 0
    print("All suite-count literals already in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
